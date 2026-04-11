"""
Salesforce Integration for Aimee MVP
Handles: account lookup, call note logging, and record updates via Salesforce REST API

Authentication: OAuth 2.0 Web Server flow (authorization code grant) ONLY.
  1. User visits /salesforce/login  → redirected to Salesforce authorization page
  2. User approves                  → Salesforce redirects to /salesforce/callback
  3. Callback exchanges the code    → calls connect_with_oauth_token() to store the token

Required env vars (Connected App settings):
  SF_CONSUMER_KEY    - Connected App consumer key
  SF_CONSUMER_SECRET - Connected App consumer secret
  SF_CALLBACK_URL    - Callback URL registered in the Connected App
                       (e.g. http://localhost:5000/salesforce/callback)
  SF_DOMAIN          - 'login' for production, 'test' for sandbox (default: login)
  FLASK_SECRET_KEY   - Flask session secret (required for CSRF state cookie)
"""

import os
import re
import logging
import requests
from datetime import datetime
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

try:
    from simple_salesforce import Salesforce
    from simple_salesforce.exceptions import (
        SalesforceAuthenticationFailed,
        SalesforceError,
        SalesforceExpiredSession,
    )
    SF_AVAILABLE = True
except ImportError:
    SF_AVAILABLE = False
    logger.warning("simple_salesforce not installed. Run: pip install simple-salesforce")


class SalesforceIntegration:
    """
    Aimee's Salesforce connector — OAuth 2.0 Web Server flow only.

    Call connect_with_oauth_token() (from the /salesforce/callback route) to
    authenticate.  Until that is called, is_connected() returns False and all
    API methods return an error dict rather than raising.
    """

    def __init__(self):
        self._sf = None
        self._connected = False
        self._refresh_token = None
        self._instance_url = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect_with_oauth_token(
        self, access_token: str, instance_url: str, refresh_token: str = None
    ) -> None:
        """
        Store an access token obtained via the OAuth2 Web Server (authorization code) flow.
        Call this from the /salesforce/callback route after exchanging the auth code.
        """
        if not SF_AVAILABLE:
            raise RuntimeError("simple_salesforce is not installed")
        self._sf = Salesforce(session_id=access_token, instance_url=instance_url)
        self._connected = True
        self._refresh_token = refresh_token
        self._instance_url = instance_url
        logger.info("Salesforce connected via OAuth2 Web Server flow (%s)", instance_url)
        print(f"[Salesforce] ✅ Connected via Web Server OAuth flow → {instance_url}")

    def is_connected(self) -> bool:
        """Return True if an OAuth token has been stored and the session is live."""
        return self._connected and self._sf is not None

    @property
    def sf(self):
        """Return the authenticated Salesforce client, or None if not yet authorised."""
        return self._sf if self._connected else None

    # ------------------------------------------------------------------
    # Account lookup
    # ------------------------------------------------------------------

    def get_account(self, account_name: str) -> dict | None:
        """
        Search for an Account by name (case-insensitive partial match).
        Returns the best-matching record dict, or None.
        """
        if not self.sf:
            return _error("Not connected to Salesforce")

        try:
            # SOQL query - partial match via LIKE
            safe_name = account_name.replace("'", "\\'")
            query = (
                f"SELECT Id, Name, Phone, BillingCity, BillingState, "
                f"AnnualRevenue, NumberOfEmployees, Type, Industry, "
                f"Description, OwnerId, Owner.Name "
                f"FROM Account "
                f"WHERE Name LIKE '%{safe_name}%' "
                f"ORDER BY Name LIMIT 5"
            )
            result = self._run(lambda sf: sf.query(query))
            records = result.get("records", [])

            if not records:
                return _error(f"No account found matching '{account_name}'")

            # Prefer exact match, fall back to first result
            exact = next(
                (r for r in records if r["Name"].lower() == account_name.lower()),
                records[0],
            )
            return {"success": True, "account": _clean_record(exact)}

        except SalesforceError as e:
            logger.error("SOQL error in get_account: %s", e)
            return _error(str(e))

    def get_account_by_id(self, account_id: str) -> dict | None:
        """Retrieve a full Account record by Salesforce ID."""
        if not self.sf:
            return _error("Not connected to Salesforce")

        try:
            record = self._run(lambda sf: sf.Account.get(account_id))
            return {"success": True, "account": _clean_record(record)}
        except SalesforceError as e:
            logger.error("get_account_by_id error: %s", e)
            return _error(str(e))

    def get_account_summary(self, account_name: str) -> str:
        """
        Return a voice-friendly summary string for an account.
        Used directly by voice_commands for TTS output.
        """
        result = self.get_account(account_name)
        if not result or not result.get("success"):
            return f"I couldn't find an account named {account_name} in Salesforce."

        acct = result["account"]
        name = acct.get("Name", account_name)
        phone = acct.get("Phone", "no phone on file")
        city = acct.get("BillingCity", "")
        state = acct.get("BillingState", "")
        location = f"{city}, {state}".strip(", ") if city or state else "location not listed"
        acct_type = acct.get("Type", "")
        owner = acct.get("Owner", {}).get("Name", "unassigned")
        revenue = acct.get("AnnualRevenue")
        revenue_str = f"Annual revenue is {_format_currency(revenue)}. " if revenue else ""

        lines = [
            f"Here's what Salesforce shows for {name}.",
            f"Account type: {acct_type}." if acct_type else "",
            f"Location: {location}.",
            f"Phone: {phone}.",
            f"{revenue_str}",
            f"Account owner: {owner}.",
        ]
        return " ".join(l for l in lines if l)

    # ------------------------------------------------------------------
    # Opportunities
    # ------------------------------------------------------------------

    def get_opportunities(self, account_name: str) -> dict:
        """Return open opportunities for an account."""
        if not self.sf:
            return _error("Not connected to Salesforce")

        account_result = self.get_account(account_name)
        if not account_result or not account_result.get("success"):
            return account_result or _error("Account not found")

        account_id = account_result["account"]["Id"]

        try:
            query = (
                f"SELECT Id, Name, StageName, Amount, CloseDate, Probability "
                f"FROM Opportunity "
                f"WHERE AccountId = '{account_id}' AND IsClosed = false "
                f"ORDER BY CloseDate ASC LIMIT 10"
            )
            result = self._run(lambda sf: sf.query(query))
            records = [_clean_record(r) for r in result.get("records", [])]
            return {
                "success": True,
                "account": account_result["account"]["Name"],
                "opportunities": records,
                "count": len(records),
            }
        except SalesforceError as e:
            logger.error("get_opportunities error: %s", e)
            return _error(str(e))

    def get_opportunity_summary(self, account_name: str) -> str:
        """Voice-friendly opportunity summary."""
        result = self.get_opportunities(account_name)
        if not result or not result.get("success"):
            return f"I couldn't retrieve opportunities for {account_name}."

        opps = result["opportunities"]
        name = result["account"]

        if not opps:
            return f"No open opportunities found for {name} in Salesforce."

        count = len(opps)
        total = sum(o.get("Amount") or 0 for o in opps)
        summary = f"{name} has {count} open {'opportunity' if count == 1 else 'opportunities'}"
        if total:
            summary += f" totaling {_format_currency(total)}"
        summary += ". "

        for opp in opps[:3]:
            opp_name = opp.get("Name", "Unnamed")
            stage = opp.get("StageName", "Unknown stage")
            close = opp.get("CloseDate", "")
            amt = opp.get("Amount")
            amt_str = f", {_format_currency(amt)}" if amt else ""
            summary += f"{opp_name}: {stage}{amt_str}, closing {close}. "

        return summary.strip()

    # ------------------------------------------------------------------
    # Contacts
    # ------------------------------------------------------------------

    def get_contacts(self, account_name: str) -> dict:
        """Return contacts for an account."""
        if not self.sf:
            return _error("Not connected to Salesforce")

        account_result = self.get_account(account_name)
        if not account_result or not account_result.get("success"):
            return account_result or _error("Account not found")

        account_id = account_result["account"]["Id"]

        try:
            query = (
                f"SELECT Id, FirstName, LastName, Title, Email, Phone, MobilePhone "
                f"FROM Contact "
                f"WHERE AccountId = '{account_id}' "
                f"ORDER BY LastName ASC LIMIT 10"
            )
            result = self._run(lambda sf: sf.query(query))
            records = [_clean_record(r) for r in result.get("records", [])]
            return {
                "success": True,
                "account": account_result["account"]["Name"],
                "contacts": records,
                "count": len(records),
            }
        except SalesforceError as e:
            logger.error("get_contacts error: %s", e)
            return _error(str(e))

    # ------------------------------------------------------------------
    # Log call notes → Salesforce Task
    # ------------------------------------------------------------------

    def log_call_note(
        self,
        account_name: str,
        subject: str,
        description: str,
        duration_minutes: int = 0,
        contact_name: str = None,
    ) -> dict:
        """
        Log a call note as a completed Task on the account.
        Optionally link to a Contact by name.
        Returns the created Task ID.
        """
        if not self.sf:
            return _error("Not connected to Salesforce")

        # Resolve account
        account_result = self.get_account(account_name)
        if not account_result or not account_result.get("success"):
            return account_result or _error(f"Account '{account_name}' not found")

        account_id = account_result["account"]["Id"]
        resolved_account_name = account_result["account"]["Name"]

        # Optionally resolve contact
        who_id = None
        if contact_name:
            contact_result = self._find_contact(contact_name, account_id)
            if contact_result:
                who_id = contact_result["Id"]

        task_data = {
            "WhatId": account_id,
            "Subject": subject or f"Call - {resolved_account_name}",
            "Description": description,
            "Status": "Completed",
            "TaskSubtype": "Call",
            "ActivityDate": datetime.today().strftime("%Y-%m-%d"),
            "CallDurationInSeconds": duration_minutes * 60 if duration_minutes else None,
            "CallType": "Outbound",
        }

        if who_id:
            task_data["WhoId"] = who_id

        # Remove None values
        task_data = {k: v for k, v in task_data.items() if v is not None}

        try:
            result = self._run(lambda sf: sf.Task.create(task_data))
            if result.get("success"):
                return {
                    "success": True,
                    "task_id": result["id"],
                    "account": resolved_account_name,
                    "subject": task_data["Subject"],
                    "message": f"Call logged for {resolved_account_name}.",
                }
            return _error("Task creation returned no ID")
        except SalesforceError as e:
            logger.error("log_call_note error: %s", e)
            return _error(str(e))

    def log_call_note_voice_summary(
        self, account_name: str, subject: str, description: str
    ) -> str:
        """Voice-friendly string after logging a call note."""
        result = self.log_call_note(account_name, subject, description)
        if result and result.get("success"):
            return f"Call note logged for {result['account']}. Task ID {result['task_id']}."
        msg = result.get("error", "Unknown error") if result else "Unknown error"
        return f"I couldn't log the call note. {msg}"

    # ------------------------------------------------------------------
    # Update account record
    # ------------------------------------------------------------------

    def update_account(self, account_name: str, fields: dict) -> dict:
        """
        Update fields on an Account record.
        fields: dict of Salesforce API field names → new values
                e.g. {"Phone": "203-555-1234", "Description": "Key account"}
        """
        if not self.sf:
            return _error("Not connected to Salesforce")

        account_result = self.get_account(account_name)
        if not account_result or not account_result.get("success"):
            return account_result or _error(f"Account '{account_name}' not found")

        account_id = account_result["account"]["Id"]
        resolved_name = account_result["account"]["Name"]

        try:
            self._run(lambda sf: sf.Account.update(account_id, fields))
            return {
                "success": True,
                "account": resolved_name,
                "updated_fields": list(fields.keys()),
                "message": f"Updated {resolved_name} in Salesforce.",
            }
        except SalesforceError as e:
            logger.error("update_account error: %s", e)
            return _error(str(e))

    def update_account_voice_summary(self, account_name: str, fields: dict) -> str:
        """Voice-friendly string after an account update."""
        result = self.update_account(account_name, fields)
        if result and result.get("success"):
            field_names = ", ".join(result["updated_fields"])
            return f"Updated {result['account']} in Salesforce. Fields changed: {field_names}."
        msg = result.get("error", "Unknown error") if result else "Unknown error"
        return f"I couldn't update the account. {msg}"

    # ------------------------------------------------------------------
    # Recent activity
    # ------------------------------------------------------------------

    def get_recent_activity(self, account_name: str, limit: int = 5) -> dict:
        """Return recent Tasks/Events for an account."""
        if not self.sf:
            return _error("Not connected to Salesforce")

        account_result = self.get_account(account_name)
        if not account_result or not account_result.get("success"):
            return account_result or _error("Account not found")

        account_id = account_result["account"]["Id"]

        try:
            query = (
                f"SELECT Id, Subject, Status, ActivityDate, Description, TaskSubtype "
                f"FROM Task "
                f"WHERE WhatId = '{account_id}' "
                f"ORDER BY ActivityDate DESC LIMIT {limit}"
            )
            result = self._run(lambda sf: sf.query(query))
            records = [_clean_record(r) for r in result.get("records", [])]
            return {
                "success": True,
                "account": account_result["account"]["Name"],
                "activities": records,
            }
        except SalesforceError as e:
            logger.error("get_recent_activity error: %s", e)
            return _error(str(e))

    def get_recent_activity_summary(self, account_name: str) -> str:
        """Voice-friendly recent activity summary."""
        result = self.get_recent_activity(account_name)
        if not result or not result.get("success"):
            return f"Couldn't retrieve activity for {account_name}."

        activities = result["activities"]
        name = result["account"]

        if not activities:
            return f"No logged activity found for {name} in Salesforce."

        summary = f"Recent activity for {name}: "
        for act in activities[:3]:
            subject = act.get("Subject", "No subject")
            date = act.get("ActivityDate", "unknown date")
            summary += f"{subject} on {date}. "
        return summary.strip()

    # ------------------------------------------------------------------
    # Connection health check
    # ------------------------------------------------------------------

    def health_check(self) -> dict:
        """Verify Salesforce connectivity and return org info."""
        if not self.sf:
            return {"connected": False, "error": "Not authenticated"}

        try:
            limits = self._run(lambda sf: sf.limits())
            return {
                "connected": True,
                "instance_url": self._sf.base_url,
                "api_calls_remaining": limits.get("DailyApiRequests", {}).get("Remaining"),
            }
        except Exception as e:
            self._connected = False
            return {"connected": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _reconnect(self) -> bool:
        """Discard the cached session and obtain a fresh token via the stored refresh token.

        Returns False (and leaves the integration unauthenticated) if no refresh
        token is available — the user must re-run the Web Server OAuth flow.
        """
        self._sf = None
        self._connected = False
        if self._refresh_token:
            return self._refresh_with_token()
        logger.warning(
            "Salesforce session expired and no refresh token is stored. "
            "Re-authenticate by visiting /salesforce/login."
        )
        print("[Salesforce] ⚠️ Session expired — visit /salesforce/login to re-authenticate.")
        return False

    def _refresh_with_token(self) -> bool:
        """Exchange the stored refresh token for a new access token."""
        consumer_key = os.getenv("SF_CONSUMER_KEY")
        consumer_secret = os.getenv("SF_CONSUMER_SECRET")
        domain = os.getenv("SF_DOMAIN", "login")

        token_url = f"https://{domain}.salesforce.com/services/oauth2/token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": consumer_key,
            "client_secret": consumer_secret,
            "refresh_token": self._refresh_token,
        }

        try:
            response = requests.post(token_url, data=payload, timeout=30)
            response.raise_for_status()
            token_data = response.json()

            access_token = token_data["access_token"]
            instance_url = token_data.get("instance_url", self._instance_url)

            self._sf = Salesforce(session_id=access_token, instance_url=instance_url)
            self._connected = True
            self._instance_url = instance_url
            logger.info("Salesforce session refreshed via refresh token")
            print("[Salesforce] ✅ Session refreshed via refresh token")
            return True
        except Exception as e:
            logger.error(
                "Salesforce token refresh failed: %s — visit /salesforce/login to re-authenticate.", e
            )
            print("[Salesforce] ❌ Token refresh failed — visit /salesforce/login to re-authenticate.")
            self._refresh_token = None
            return False

    def _run(self, api_call):
        """
        Execute api_call(sf_client), automatically reconnecting once if the
        access token has expired.  All other exceptions propagate normally.
        """
        try:
            return api_call(self._sf)
        except SalesforceExpiredSession:
            logger.info("Salesforce session expired — reconnecting")
            print("[Salesforce] Session expired, reconnecting…")
            if not self._reconnect():
                raise
            return api_call(self._sf)

    def _find_contact(self, contact_name: str, account_id: str) -> dict | None:
        """Find a contact by name within an account."""
        try:
            safe_name = contact_name.replace("'", "\\'")
            query = (
                f"SELECT Id, FirstName, LastName "
                f"FROM Contact "
                f"WHERE AccountId = '{account_id}' "
                f"AND (FirstName LIKE '%{safe_name}%' OR LastName LIKE '%{safe_name}%') "
                f"LIMIT 1"
            )
            result = self._run(lambda sf: sf.query(query))
            records = result.get("records", [])
            return records[0] if records else None
        except Exception:
            return None


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_instance: SalesforceIntegration | None = None


def get_salesforce() -> SalesforceIntegration:
    """Return the module-level Salesforce singleton.

    The instance is NOT pre-connected.  Authentication happens when the user
    completes the OAuth 2.0 Web Server flow (/salesforce/login → /salesforce/callback),
    which calls connect_with_oauth_token() on the returned instance.
    """
    global _instance
    if _instance is None:
        _instance = SalesforceIntegration()
    return _instance


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def _clean_record(record: dict) -> dict:
    """Strip Salesforce metadata keys from a record dict."""
    return {k: v for k, v in record.items() if not k.startswith("attributes")}


def _error(message: str) -> dict:
    return {"success": False, "error": message}


def _format_currency(value) -> str:
    """Format a numeric value as a dollar string."""
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)
