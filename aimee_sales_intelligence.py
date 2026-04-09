#!/usr/bin/env python3
"""
Aimee Sales Intelligence Engine
The ultimate wine sales AI that makes reps money
"""

import json
import datetime
from typing import Dict, List, Optional

class AimeeSalesIntelligence:
    def __init__(self, data_file="aimee_sales_intelligence_data.json"):
        self.load_sales_data(data_file)
        
    def load_sales_data(self, data_file):
        """Load comprehensive sales intelligence data"""
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
                self.customers = data.get("customer_profiles", {})
                self.competitive_intel = data.get("competitive_intelligence", {})
                self.territory_insights = data.get("territory_insights", {})
                self.sales_insights = data.get("sales_insights", {})
        except FileNotFoundError:
            print(f"Warning: {data_file} not found")
            self.customers = {}
            self.competitive_intel = {}
            self.territory_insights = {}
            self.sales_insights = {}
    
    def get_daily_priorities(self) -> str:
        """Generate daily priority briefing for sales rep"""
        priorities = self.sales_insights.get("daily_priorities", [])
        
        if not priorities:
            return "No priority accounts identified for today."
        
        response = "Here are your top priorities today:\n\n"
        
        for i, priority in enumerate(priorities, 1):
            account_name = self.customers.get(priority["account"], {}).get("company_name", priority["account"])
            urgency = priority["priority"].upper()
            action = priority["action"].replace("_", " ").title()
            reason = priority["reason"]
            opportunity = priority["opportunity"]
            
            response += f"**Priority {i} - {urgency}**: {account_name}\n"
            response += f"Action: {action}\n"
            response += f"Why: {reason}\n"
            response += f"Opportunity: {opportunity}\n\n"
        
        return response
    
    def get_account_briefing(self, account_key: str) -> str:
        """Get comprehensive account intelligence"""
        if account_key not in self.customers:
            # Try fuzzy matching
            for key, customer in self.customers.items():
                if account_key.lower() in customer.get("company_name", "").lower():
                    account_key = key
                    break
            else:
                return f"Account '{account_key}' not found in database."
        
        customer = self.customers[account_key]
        
        # Calculate key metrics
        annual_volume = customer.get("annual_volume", 0)
        annual_margin = customer.get("annual_margin", 0)
        margin_percent = (annual_margin / annual_volume * 100) if annual_volume > 0 else 0
        
        # Payment status
        overdue = customer.get("days_overdue", 0)
        outstanding = customer.get("outstanding_balance", 0)
        
        # Trend analysis
        trend = customer.get("order_trend", 0)
        trend_text = f"+{trend}%" if trend > 0 else f"{trend}%" if trend < 0 else "flat"
        
        response = f"**{customer.get('company_name')}** - Account Intelligence\n\n"
        response += f"**Financial Profile:**\n"
        response += f"• Annual Volume: ${annual_volume:,}\n"
        response += f"• Annual Margin: ${annual_margin:,} ({margin_percent:.1f}%)\n"
        response += f"• Average Order: ${customer.get('avg_order_size', 0):,}\n"
        response += f"• Payment Terms: {customer.get('payment_terms', 'Unknown')}\n"
        
        if outstanding > 0:
            response += f"• Outstanding Balance: ${outstanding:,}"
            if overdue > 0:
                response += f" ({overdue} days overdue) ⚠️"
            response += "\n"
        
        response += f"\n**Buying Behavior:**\n"
        response += f"• Order Frequency: Every {customer.get('order_frequency_days', 'Unknown')} days\n"
        response += f"• Recent Trend: {trend_text}\n"
        response += f"• Price Sensitivity: {customer.get('price_sensitivity', 'Unknown').title()}\n"
        response += f"• Preferred Categories: {', '.join(customer.get('preferred_categories', []))}\n"
        
        response += f"\n**Strategic Intel:**\n"
        response += f"• Decision Maker: {customer.get('decision_maker', 'Unknown')}\n"
        response += f"• Opportunity Score: {customer.get('opportunity_score', 0)}/100\n"
        response += f"• Risk Score: {customer.get('risk_score', 0)}/100\n"
        response += f"• Account Tier: {customer.get('account_tier', 'Unknown').title()}\n"
        
        # Competitive threats
        threats = customer.get("competitive_threats", [])
        if threats:
            response += f"• Competitive Threats: {', '.join(threats)}\n"
        
        response += f"\n**Notes:** {customer.get('account_notes', 'No notes available')}\n"
        
        # Upsell opportunities
        upsells = customer.get("upsell_opportunities", [])
        if upsells:
            response += f"\n**Upsell Opportunities:** {', '.join(upsells)}"
        
        return response
    
    def get_competitive_battle_card(self, competitor: str) -> str:
        """Get competitive intelligence and battle cards"""
        competitor_key = competitor.lower().replace(" ", "_").replace("-", "_")
        
        if competitor_key not in self.competitive_intel:
            return f"No competitive intelligence available for {competitor}."
        
        intel = self.competitive_intel[competitor_key]
        
        response = f"**{competitor.title()} - Competitive Battle Card**\n\n"
        
        response += f"**Their Strengths:**\n"
        for strength in intel.get("strengths", []):
            response += f"• {strength}\n"
        
        response += f"\n**Their Weaknesses:**\n"
        for weakness in intel.get("weaknesses", []):
            response += f"• {weakness}\n"
        
        response += f"\n**Battle Cards - How to Win:**\n"
        battle_cards = intel.get("battle_cards", {})
        for objection, response_text in battle_cards.items():
            response += f"• **{objection.replace('_', ' ').title()}**: {response_text}\n"
        
        return response
    
    def get_upsell_recommendations(self, account_key: str) -> str:
        """Generate smart upsell recommendations"""
        if account_key not in self.customers:
            return f"Account '{account_key}' not found."
        
        customer = self.customers[account_key]
        annual_volume = customer.get("annual_volume", 0)
        margin = customer.get("annual_margin", 0)
        
        response = f"**Upsell Opportunities for {customer.get('company_name')}**\n\n"
        
        # Calculate potential revenue impact
        upsells = customer.get("upsell_opportunities", [])
        
        if "Premium glassware" in upsells:
            potential_revenue = annual_volume * 0.15  # 15% of wine volume
            response += f"• **Premium Glassware Program**: ${potential_revenue:,.0f} potential revenue\n"
            response += f"  - Enhances wine presentation and customer experience\n"
            response += f"  - 40% margin on glassware vs 20% on wine\n\n"
        
        if "Wine storage solutions" in upsells:
            potential_revenue = 25000  # Fixed opportunity
            response += f"• **Wine Storage Solutions**: ${potential_revenue:,.0f} potential revenue\n"
            response += f"  - Proper storage increases wine quality and reduces waste\n"
            response += f"  - High-margin service offering\n\n"
        
        if "Staff training" in upsells:
            potential_revenue = 5000  # Training fee
            response += f"• **Staff Wine Training**: ${potential_revenue:,.0f} training revenue + 25% wine sales increase\n"
            response += f"  - Trained staff sell 25% more wine per customer\n"
            response += f"  - Builds loyalty and expertise\n\n"
        
        if "House wine program" in upsells:
            potential_revenue = annual_volume * 0.3  # 30% increase
            response += f"• **House Wine Program**: ${potential_revenue:,.0f} potential annual increase\n"
            response += f"  - Cost-effective quality wines with your branding\n"
            response += f"  - Higher margins than branded wines\n\n"
        
        # Smart recommendations based on data
        price_sensitivity = customer.get("price_sensitivity", "medium")
        if price_sensitivity == "low" and annual_volume > 1000000:
            response += f"• **Exclusive Allocations**: Target rare wines - low price sensitivity indicates premium opportunity\n"
        
        if customer.get("order_trend", 0) > 10:
            response += f"• **Volume Discount Program**: Growing {customer.get('order_trend')}% - lock in growth with volume commitments\n"
        
        return response
    
    def get_deal_closing_strategy(self, account_key: str) -> str:
        """Generate deal closing strategy based on account intelligence"""
        if account_key not in self.customers:
            return f"Account '{account_key}' not found."
        
        customer = self.customers[account_key]
        
        response = f"**Deal Closing Strategy for {customer.get('company_name')}**\n\n"
        
        # Analyze key factors
        price_sensitivity = customer.get("price_sensitivity", "medium")
        opportunity_score = customer.get("opportunity_score", 50)
        risk_score = customer.get("risk_score", 50)
        outstanding_balance = customer.get("outstanding_balance", 0)
        days_overdue = customer.get("days_overdue", 0)
        
        response += f"**Closing Probability**: {opportunity_score}% (Risk: {risk_score}%)\n\n"
        
        # Payment considerations
        if outstanding_balance > 0:
            response += f"⚠️ **Payment Issue**: ${outstanding_balance:,} outstanding"
            if days_overdue > 0:
                response += f" ({days_overdue} days overdue)"
            response += f"\n• **Strategy**: Address payment before new orders\n• **Approach**: Offer payment plan + volume discount\n\n"
        
        # Price sensitivity strategy
        if price_sensitivity == "high":
            response += f"💰 **Price Sensitive Account**\n"
            response += f"• Lead with value proposition, not price\n"
            response += f"• Emphasize cost-per-pour and margin improvement\n"
            response += f"• Offer volume discounts for commitment\n\n"
        elif price_sensitivity == "low":
            response += f"💎 **Premium Focused Account**\n"
            response += f"• Lead with quality and exclusivity\n"
            response += f"• Emphasize rare allocations and prestige\n"
            response += f"• Price is secondary to value\n\n"
        
        # Competitive threats
        threats = customer.get("competitive_threats", [])
        if threats:
            response += f"⚔️ **Competitive Pressure from**: {', '.join(threats)}\n"
            response += f"• **Strategy**: Emphasize relationship and service\n"
            response += f"• **Urgency**: Create time-limited exclusive offers\n\n"
        
        # Timing strategy
        order_frequency = customer.get("order_frequency_days")
        if order_frequency:
            last_order = customer.get("last_order_date")
            if last_order:
                # Calculate next expected order (simplified)
                response += f"📅 **Timing**: Orders every {order_frequency} days\n"
                response += f"• **Best Contact Time**: 3-5 days before expected reorder\n"
                response += f"• **Urgency Trigger**: Inventory running low\n\n"
        
        # Decision maker strategy
        decision_maker = customer.get("decision_maker", "")
        if decision_maker:
            response += f"👤 **Decision Maker**: {decision_maker}\n"
            if "owner" in decision_maker.lower():
                response += f"• **Approach**: Focus on business growth and profitability\n"
            elif "buyer" in decision_maker.lower():
                response += f"• **Approach**: Focus on product quality and vendor reliability\n"
            elif "wine director" in decision_maker.lower():
                response += f"• **Approach**: Focus on wine expertise and customer satisfaction\n"
        
        return response

# Handler functions for integration with main pipeline
def handle_daily_priorities(sales_intelligence: AimeeSalesIntelligence) -> str:
    """Handle daily priority requests"""
    return sales_intelligence.get_daily_priorities()

def handle_account_briefing(account_name: str, sales_intelligence: AimeeSalesIntelligence) -> str:
    """Handle account briefing requests"""
    # Convert company name to account key
    account_key = account_name.lower().replace(" ", "_").replace("'", "").replace("&", "and")
    return sales_intelligence.get_account_briefing(account_key)

def handle_competitive_intel(competitor: str, sales_intelligence: AimeeSalesIntelligence) -> str:
    """Handle competitive intelligence requests"""
    return sales_intelligence.get_competitive_battle_card(competitor)

def handle_upsell_opportunities(account_name: str, sales_intelligence: AimeeSalesIntelligence) -> str:
    """Handle upsell opportunity requests"""
    account_key = account_name.lower().replace(" ", "_").replace("'", "").replace("&", "and")
    return sales_intelligence.get_upsell_recommendations(account_key)

def handle_deal_strategy(account_name: str, sales_intelligence: AimeeSalesIntelligence) -> str:
    """Handle deal closing strategy requests"""
    account_key = account_name.lower().replace(" ", "_").replace("'", "").replace("&", "and")
    return sales_intelligence.get_deal_closing_strategy(account_key)