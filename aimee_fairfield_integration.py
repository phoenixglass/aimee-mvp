# aimee_fairfield_integration.py
# Enhanced Fairfield County restaurant and distributor intelligence with tactical briefings

import json
from typing import Dict, List, Optional
from datetime import datetime
import re

class FairfieldCountyIntelligence:
    def __init__(self):
        # TACTICAL BRIEFINGS - All 17 accounts from Customer_Tactical_Briefings.docx
        self.tactical_briefings = {
            # RESTAURANTS
            "spiga": {
                "name": "Spiga Wine Bar",
                "location": "New Canaan",
                "type": "restaurant",
                "annual_volume": "$400K-$600K",
                "tactical_brief": "High-end Italian trattoria in ultra-wealthy New Canaan. Handmade pastas, brick oven pizza, deep glass + reserve list. Owner-run by Dan Camporeale - expect deep knowledge. Lead with exclusive Italian allocations. Pitch pairing dinners + private cellar curation. Bring prestige.",
                "voice_response": "Spiga Wine Bar, New Canaan. High-end Italian trattoria in ultra-wealthy New Canaan. 400K to 600K annual wine spend. Owner-run by Dan Camporeale, expect deep knowledge. Lead with exclusive Italian allocations. Pitch pairing dinners and private cellar curation. Bring prestige."
            },
            "barcelona_norwalk": {
                "name": "Barcelona Wine Bar - Norwalk",
                "location": "Norwalk (Waypointe)",
                "type": "restaurant",
                "annual_volume": "$1M+",
                "tactical_brief": "Old World focus, bold Basque flavors. 500+ bottle list, 40+ by the glass - heavy Spanish influence, strong on biodynamic/natural. Chef Misha Ryklin leads with punchy pintxos and deep pairings. Staff is sharp. Gaps: rare Rioja, super-premium Cava, micro-lot naturals. Bring depth and exclusivity. Sell like you're curating a cellar.",
                "voice_response": "Barcelona Wine Bar Norwalk. Old World focus, bold Basque flavors. 500 plus bottle list, 40 plus by the glass. Heavy Spanish influence, strong on biodynamic and natural wines. Chef Misha Ryklin leads with punchy pintxos and deep pairings. Staff is sharp. Gaps include rare Rioja, super-premium Cava, micro-lot naturals. One million plus wine program. Sell like you're curating a cellar."
            },
            "barcelona_fairfield": {
                "name": "Barcelona Wine Bar - Fairfield",
                "location": "Fairfield",
                "type": "restaurant",
                "annual_volume": "$1M",
                "tactical_brief": "High-volume flagship. Mediterranean-Spanish blend with seasonal menus. Chef Ted Gola runs a cleaner, more polished culinary play. Known for Wine & Swine events - strong experiential potential. Wine list lighter on rare vintage Spanish, room to grow in rosé + private label. Staff expects excellence. Show up with story-driven allocations and event-ready pairings.",
                "voice_response": "Barcelona Wine Bar Fairfield. High-volume flagship. One million annual wine spend. Mediterranean-Spanish blend with seasonal menus. Chef Ted Gola runs a cleaner, more polished culinary play. Known for Wine and Swine events, strong experiential potential. Wine list lighter on rare vintage Spanish, room to grow in rosé and private label. Staff expects excellence. Show up with story-driven allocations and event-ready pairings."
            },
            "elm": {
                "name": "ELM",
                "location": "New Canaan",
                "type": "restaurant",
                "annual_volume": "$500K-$700K",
                "tactical_brief": "Refined New American led by Chef Luke Venner. Seasonal, elegant, ingredient-first. Cool-climate Old World focus: Burgundy, Champagne, Supertuscans, rosé. By-the-glass includes Roederer, Domaine Ott, Insoglio - expect sophistication. Gaps: no natural wines, limited grower Champagne, room for Loire + German whites. Hosts boutique wine dinners. Lead with terroir-driven, small-lot finds. Sell the story, not the spec sheet.",
                "voice_response": "ELM, New Canaan. Refined New American led by Chef Luke Venner. Seasonal, elegant, ingredient-first. 500K to 700K wine program. Cool-climate Old World focus: Burgundy, Champagne, Supertuscans, rosé. By-the-glass includes Roederer, Domaine Ott, Insoglio. Expect sophistication. Gaps include no natural wines, limited grower Champagne, room for Loire and German whites. Hosts boutique wine dinners. Lead with terroir-driven, small-lot finds. Sell the story, not the spec sheet."
            },
            "the_cottage": {
                "name": "The Cottage",
                "location": "Westport",
                "type": "restaurant",
                "annual_volume": "$600K+",
                "tactical_brief": "Chef Brian Lewis's flagship. Seasonal New American with global technique and local pride. Tight and thoughtful wine program. Current list: grower Champagne, Chassagne-Montrachet, Brunello, Châteauneuf. Expect sophistication, not flash. Gaps: limited biodynamic and natural wines, space for rare allocations. 'Ten Year Tasting' menu = perfect entry for pairing collabs. Lead with terroir, scarcity, and story. Elevate their edge.",
                "voice_response": "The Cottage, Westport. Chef Brian Lewis's flagship. Seasonal New American with global technique and local pride. 600K plus wine program, tight and thoughtful. Current list includes grower Champagne, Chassagne-Montrachet, Brunello, Châteauneuf. Expect sophistication, not flash. Gaps include limited biodynamic and natural wines, space for rare allocations. Ten Year Tasting menu equals perfect entry for pairing collabs. Lead with terroir, scarcity, and story. Elevate their edge."
            },
            "bin_100": {
                "name": "Bin 100",
                "location": "Milford, CT",
                "type": "restaurant",
                "annual_volume": "$600K+",
                "tactical_brief": "Modern Italian-Mediterranean with a polished edge. Chef-driven menu - lobster ravioli, wild boar ragù, NY strip Diane. Glass list runs from Valdo Prosecco to Louis Martini Cab. Bottle list flexes from Ferrari Brut to Dom Pérignon and Cristal. Orin Swift by the glass. Hosts multi-course wine dinners with boutique producers. Gaps: minimal natural wines, limited grower Champagne, room for Loire whites and German Rieslings. Lead with terroir-driven, small-lot finds. Sell the story, not the spec sheet.",
                "voice_response": "Bin 100, Milford Connecticut. Modern Italian-Mediterranean with a polished edge. Chef-driven menu including lobster ravioli, wild boar ragù, New York strip Diane. 600K plus wine program. Glass list runs from Valdo Prosecco to Louis Martini Cab. Bottle list flexes from Ferrari Brut to Dom Pérignon and Cristal. Orin Swift by the glass. Hosts multi-course wine dinners with boutique producers. Gaps include minimal natural wines, limited grower Champagne, room for Loire whites and German Rieslings. Lead with terroir-driven, small-lot finds. Sell the story, not the spec sheet."
            },
            "blackstones_grille": {
                "name": "Blackstones Grille",
                "location": "Southport (Fairfield, CT)",
                "type": "restaurant",
                "annual_volume": "$500K-$700K",
                "tactical_brief": "Classic steakhouse with Mediterranean flair. USDA Prime dry-aged cuts, seafood, and pasta. Wine list includes grower Champagne, Chassagne-Montrachet, Brunello, and Châteauneuf. Gaps: limited natural wines, room for rare allocations. Lead with terroir-driven, small-lot finds. Sell the story, not the spec sheet.",
                "voice_response": "Blackstones Grille, Southport Fairfield Connecticut. Classic steakhouse with Mediterranean flair. USDA Prime dry-aged cuts, seafood, and pasta. 500K to 700K wine program. Wine list includes grower Champagne, Chassagne-Montrachet, Brunello, and Châteauneuf. Gaps include limited natural wines, room for rare allocations. Lead with terroir-driven, small-lot finds. Sell the story, not the spec sheet."
            },
            "blackstones_norwalk": {
                "name": "Blackstones Steakhouse - Norwalk",
                "location": "Norwalk",
                "type": "restaurant",
                "annual_volume": "Not specified",
                "tactical_brief": "Upscale, traditional steakhouse in downtown Norwalk. Big pours, big names - Prime cuts, seafood towers, and a 500+ bottle wine cellar. Known labels like First Press Cab and Penfolds dominate the list. Crowd skews business and upscale locals. Gaps: little to no small-lot or story-driven wines, limited differentiation. Lead with bold, premium reds that overdeliver. Position lesser-known labels as exclusives. Help them stand out in a saturated steakhouse market. Sell prestige with a twist.",
                "voice_response": "Blackstones Steakhouse Norwalk. Upscale, traditional steakhouse in downtown Norwalk. Big pours, big names. Prime cuts, seafood towers, and a 500 plus bottle wine cellar. Known labels like First Press Cab and Penfolds dominate the list. Crowd skews business and upscale locals. Gaps include little to no small-lot or story-driven wines, limited differentiation. Lead with bold, premium reds that overdeliver. Position lesser-known labels as exclusives. Help them stand out in a saturated steakhouse market. Sell prestige with a twist."
            },
            "blackstones_stamford": {
                "name": "Blackstones Steakhouse - Stamford",
                "location": "Stamford",
                "type": "restaurant",
                "annual_volume": "Not specified",
                "tactical_brief": "Power steakhouse in downtown Stamford. Loud, upscale, and high-traffic. Big pours, brand-name bottles - think Caymus, Silver Oak, Dom. Wine list favors reputation over risk. Gaps: zero boutique identity, room for premium-but-unknown. Lead with recognizable prestige or story-rich labels with presence. Pitch flash-in-the-glass - something that impresses at the table and justifies the tab. Sell status, not subtlety.",
                "voice_response": "Blackstones Steakhouse Stamford. Power steakhouse in downtown Stamford. Loud, upscale, and high-traffic. Big pours, brand-name bottles including Caymus, Silver Oak, Dom. Wine list favors reputation over risk. Gaps include zero boutique identity, room for premium-but-unknown. Lead with recognizable prestige or story-rich labels with presence. Pitch flash-in-the-glass, something that impresses at the table and justifies the tab. Sell status, not subtlety."
            },
            "rebeccas": {
                "name": "Rebecca's",
                "location": "Greenwich",
                "type": "restaurant",
                "annual_volume": "Not specified",
                "tactical_brief": "White-tablecloth power dining in mid-country Greenwich. Chef-owned, ultra-refined, $300 prix fixe. Menu leans modern French - think foie gras terrine, Kobe NY strip, truffle risotto. Wine list favors Burgundy and top-tier California, updated daily. No fluff, no filler. Gaps: limited small-lot imports, opportunity for rare allocations. Audience expects rarity and elegance. Lead with terroir, vintage depth, and pristine provenance. If it's on the list, it better be exceptional. This is collector territory - sell accordingly.",
                "voice_response": "Rebecca's, Greenwich. White-tablecloth power dining in mid-country Greenwich. Chef-owned, ultra-refined, 300 dollar prix fixe. Menu leans modern French including foie gras terrine, Kobe New York strip, truffle risotto. Wine list favors Burgundy and top-tier California, updated daily. No fluff, no filler. Gaps include limited small-lot imports, opportunity for rare allocations. Audience expects rarity and elegance. Lead with terroir, vintage depth, and pristine provenance. If it's on the list, it better be exceptional. This is collector territory, sell accordingly."
            },
            
            # RETAIL STORES
            "99_bottles": {
                "name": "99 Bottles",
                "location": "Westport",
                "type": "retail",
                "annual_volume": "Not specified",
                "tactical_brief": "Saugatuck staple. Curated, neighborhood-focused wine + spirits shop. Strong local loyalty, premium tastes, and high-touch service. Program skews broad but approachable. Gaps: limited natural wines, room for rare small-batch allocations. Customers ask for unique - store delivers when it can. Smart entry: exclusive terroir wines with a story. Offer tastings, staff education, and tight seasonal drops. Sell the shelf, but win the rep.",
                "voice_response": "99 Bottles, Westport. Saugatuck staple. Curated, neighborhood-focused wine and spirits shop. Strong local loyalty, premium tastes, and high-touch service. Program skews broad but approachable. Gaps include limited natural wines, room for rare small-batch allocations. Customers ask for unique, store delivers when it can. Smart entry: exclusive terroir wines with a story. Offer tastings, staff education, and tight seasonal drops. Sell the shelf, but win the rep."
            },
            "horseneck": {
                "name": "Horseneck Wine & Spirits",
                "location": "Greenwich",
                "type": "retail",
                "annual_volume": "Not specified",
                "tactical_brief": "Greenwich institution since 1934. Elite clientele, cellar-grade curation. Heavy focus on natural, organic, and biodynamic wines - plus serious Burgundy, Bordeaux, and Italy. Offers a tight, story-driven wine club and same-day local delivery. Gaps? Few. But they're always hunting standout small-lot bottles with narrative weight. Lead with terroir, scarcity, and philosophy. If it's just juice in a bottle, don't bother.",
                "voice_response": "Horseneck Wine and Spirits, Greenwich. Greenwich institution since 1934. Elite clientele, cellar-grade curation. Heavy focus on natural, organic, and biodynamic wines, plus serious Burgundy, Bordeaux, and Italy. Offers a tight, story-driven wine club and same-day local delivery. Gaps are few. But they're always hunting standout small-lot bottles with narrative weight. Lead with terroir, scarcity, and philosophy. If it's just juice in a bottle, don't bother."
            },
            "db_fine_wines": {
                "name": "DB Fine Wines",
                "location": "New Canaan, CT",
                "type": "retail",
                "annual_volume": "Not specified",
                "tactical_brief": "Boutique wine shop with a curated selection of artisanal, low-production wines. Owner David Fieber emphasizes quality over ratings, focusing on small-scale producers from regions like Bordeaux, Tuscany, and Napa Valley. The store offers personalized recommendations, maintains customer preference records, and hosts themed tastings. Recognized with multiple Wine-Searcher Retailer Awards for its diverse selections. Ideal for introducing terroir-driven, exclusive allocations.",
                "voice_response": "DB Fine Wines, New Canaan Connecticut. Boutique wine shop with a curated selection of artisanal, low-production wines. Owner David Fieber emphasizes quality over ratings, focusing on small-scale producers from regions like Bordeaux, Tuscany, and Napa Valley. The store offers personalized recommendations, maintains customer preference records, and hosts themed tastings. Recognized with multiple Wine-Searcher Retailer Awards for its diverse selections. Ideal for introducing terroir-driven, exclusive allocations."
            },
            "greens_farms": {
                "name": "Greens Farms Spirit Shop",
                "location": "Westport",
                "type": "retail",
                "annual_volume": "Not specified",
                "tactical_brief": "Westport mainstay since 1969. Fine wine, craft spirits, and high-end bourbon in a well-trafficked retail location. Saturday tastings draw serious regulars. Staff is service-driven - known for free delivery, gift wrapping, and customer retention. Gaps: opportunity to elevate natural wine offerings and add exclusive small-lot labels. Lead with boutique, terroir-first selections that show well in-store. Offer tasting support and drop-in education. Quality sells here - make it personal.",
                "voice_response": "Greens Farms Spirit Shop, Westport. Westport mainstay since 1969. Fine wine, craft spirits, and high-end bourbon in a well-trafficked retail location. Saturday tastings draw serious regulars. Staff is service-driven, known for free delivery, gift wrapping, and customer retention. Gaps include opportunity to elevate natural wine offerings and add exclusive small-lot labels. Lead with boutique, terroir-first selections that show well in-store. Offer tasting support and drop-in education. Quality sells here, make it personal."
            },
            "labellas": {
                "name": "LaBella's Fine Wine & Spirits",
                "location": "Riverside, CT",
                "type": "retail",
                "annual_volume": "Not specified",
                "tactical_brief": "Family-owned boutique since 2010. Mauricio & Kimberly Zapata curate a refined, globally sourced selection with a personal touch. Strong in Bordeaux, Tuscany, Napa, and Champagne. Known for personalized service, custom gift baskets, and stylish gift-wrapping. Gaps: limited natural wines, room for exclusive small-lot allocations. Lead with terroir-driven, story-rich selections that align with their curated approach. Emphasize how these offerings can enhance their personalized customer experience.",
                "voice_response": "LaBella's Fine Wine and Spirits, Riverside Connecticut. Family-owned boutique since 2010. Mauricio and Kimberly Zapata curate a refined, globally sourced selection with a personal touch. Strong in Bordeaux, Tuscany, Napa, and Champagne. Known for personalized service, custom gift baskets, and stylish gift-wrapping. Gaps include limited natural wines, room for exclusive small-lot allocations. Lead with terroir-driven, story-rich selections that align with their curated approach. Emphasize how these offerings can enhance their personalized customer experience."
            },
            "acme_liquors": {
                "name": "Acme Liquors",
                "location": "New Canaan",
                "type": "retail",
                "annual_volume": "Not specified",
                "tactical_brief": "No-frills local shop on Elm Street. Steady neighborhood traffic, convenient location, broad base. Selection skews traditional - safe labels, familiar regions. No known wine curation program. Gaps: no visibility into natural, biodynamic, or small-lot options. Smart inroad: introduce approachable, exclusive bottles with strong margins and shelf appeal. Offer staff training or tasting support. Simplicity and reliability win here. Don't overcomplicate.",
                "voice_response": "Acme Liquors, New Canaan. No-frills local shop on Elm Street. Steady neighborhood traffic, convenient location, broad base. Selection skews traditional, safe labels, familiar regions. No known wine curation program. Gaps include no visibility into natural, biodynamic, or small-lot options. Smart inroad: introduce approachable, exclusive bottles with strong margins and shelf appeal. Offer staff training or tasting support. Simplicity and reliability win here. Don't overcomplicate."
            }
        }
        
        # DISTRIBUTORS - Keep existing data
        self.distributors = {
            "cdi_breakthru": {
                "name": "CDI/Breakthru Beverage",
                "coverage": "Statewide Connecticut",
                "specialties": ["Premium wines", "Craft spirits", "National brands"],
                "key_contact": "Regional Sales Manager",
                "relationship_status": "Strong partnership",
                "recent_activity": "New Italian portfolio launch"
            },
            "martignetti": {
                "name": "Martignetti Companies",
                "coverage": "Connecticut & Massachusetts", 
                "specialties": ["Fine wine", "Premium imports", "Restaurant focus"],
                "key_contact": "CT Sales Director",
                "relationship_status": "Active collaboration",
                "recent_activity": "Bordeaux allocation discussions"
            },
            "murphy": {
                "name": "Murphy Distributors",
                "coverage": "Fairfield County",
                "specialties": ["Local restaurants", "Quick delivery", "Flexible terms"],
                "key_contact": "Account Manager",
                "relationship_status": "Reliable partner",
                "recent_activity": "Weekend delivery service expansion"
            },
            "missing_link": {
                "name": "Missing Link Wine Co",
                "coverage": "Boutique accounts Connecticut",
                "specialties": ["Natural wines", "Small producers", "Unique selections"],
                "key_contact": "Owner/Buyer",
                "relationship_status": "Niche partnership",
                "recent_activity": "New natural wine program"
            }
        }
        
    def get_daily_priorities(self) -> str:
        """Generate daily priority briefing with tactical focus"""
        today = datetime.now().strftime("%A, %B %d")
        
        priorities = [
            "🎯 Barcelona Norwalk: Follow up on Basque natural wine program - 1M+ pipeline",
            "📞 ELM New Canaan: Boutique wine dinner prep - terroir-driven focus",
            "💼 Bin 100: Multi-course wine dinner opportunity - 600K+ account", 
            "🍷 Spiga: Dan Camporeale private cellar curation meeting",
            "📈 The Cottage: Ten Year Tasting menu pairing collaboration",
            "🏢 Horseneck: Elite clientele small-lot bottle hunting session"
        ]
        
        response = f"⚡ Daily Tactical Priorities - {today}:\n\n"
        response += "\n".join(priorities)
        response += f"\n\n💰 Active Pipeline: $3.5M+ across 17 premium accounts"
        response += f"\n🎯 Today's Focus: Natural wine expansion and exclusive allocations"
        response += f"\n💡 Key Edge: You move faster, know the gaps, bring the stories they need."
        
        return response
    
    def get_tactical_briefing(self, account_name: str) -> str:
        """Get tactical briefing for specific account"""
        account_key = self._normalize_account_name(account_name)
        
        if account_key in self.tactical_briefings:
            account = self.tactical_briefings[account_key]
            
            # Format for voice delivery
            response = f"🎯 TACTICAL BRIEF: {account['name']}\n\n"
            response += f"📍 {account['location']} | "
            if account['annual_volume'] != "Not specified":
                response += f"💰 {account['annual_volume']} | "
            response += f"🏪 {account['type'].title()}\n\n"
            response += f"⚡ TACTICAL INTELLIGENCE:\n{account['tactical_brief']}\n\n"
            response += "💡 Execute with precision. Strike clean. Next."
            
            return response
        else:
            return self._suggest_accounts(account_name)
    
    def get_voice_briefing(self, account_name: str) -> str:
        """Get voice-optimized briefing for TTS"""
        account_key = self._normalize_account_name(account_name)
        
        if account_key in self.tactical_briefings:
            account = self.tactical_briefings[account_key]
            return account['voice_response']
        else:
            return f"Account not found. I have tactical intelligence on 17 Fairfield County accounts including Barcelona Wine Bar, Spiga, ELM, The Cottage, Bin 100, Horseneck Wine and Spirits, and others. Which account would you like briefed?"
    
    def get_regional_briefing(self, region: str) -> str:
        """Get briefing by geographic region"""
        region_lower = region.lower()
        
        if "new canaan" in region_lower:
            accounts = ["spiga", "elm", "db_fine_wines", "acme_liquors"]
            region_name = "New Canaan"
        elif "westport" in region_lower:
            accounts = ["the_cottage", "99_bottles", "greens_farms"]
            region_name = "Westport"
        elif "norwalk" in region_lower:
            accounts = ["barcelona_norwalk", "blackstones_norwalk"]
            region_name = "Norwalk"
        elif "fairfield" in region_lower:
            accounts = ["barcelona_fairfield", "blackstones_grille"]
            region_name = "Fairfield"
        elif "stamford" in region_lower:
            accounts = ["blackstones_stamford"]
            region_name = "Stamford"
        elif "greenwich" in region_lower:
            accounts = ["rebeccas", "horseneck"]
            region_name = "Greenwich"
        else:
            return "Available regions: New Canaan, Westport, Norwalk, Fairfield, Stamford, Greenwich. Which region would you like briefed?"
        
        response = f"🗺️ {region_name} Market Intelligence:\n\n"
        
        total_value = 0
        account_count = len(accounts)
        
        for account_key in accounts:
            if account_key in self.tactical_briefings:
                account = self.tactical_briefings[account_key]
                response += f"▪️ {account['name']} ({account['type'].title()})\n"
                if account['annual_volume'] != "Not specified":
                    response += f"   💰 {account['annual_volume']}\n"
                response += f"   🎯 {account['tactical_brief'][:100]}...\n\n"
        
        response += f"📊 {region_name} Summary: {account_count} premium accounts\n"
        response += f"💡 Regional Strategy: Lead with local market knowledge and targeted approach per venue type."
        
        return response
    
    def get_multi_location_briefing(self, chain: str) -> str:
        """Get briefing for multi-location accounts"""
        if "blackstones" in chain.lower():
            accounts = ["blackstones_grille", "blackstones_norwalk", "blackstones_stamford"]
            chain_name = "Blackstones"
        elif "barcelona" in chain.lower():
            accounts = ["barcelona_norwalk", "barcelona_fairfield"]
            chain_name = "Barcelona Wine Bar"
        else:
            return "Multi-location briefings available for: Blackstones (3 locations), Barcelona Wine Bar (2 locations)."
        
        response = f"🏢 {chain_name} Multi-Location Intelligence:\n\n"
        
        for account_key in accounts:
            if account_key in self.tactical_briefings:
                account = self.tactical_briefings[account_key]
                response += f"📍 {account['name']} - {account['location']}\n"
                if account['annual_volume'] != "Not specified":
                    response += f"   💰 {account['annual_volume']}\n"
                response += f"   🎯 Key Approach: {account['tactical_brief'][:150]}...\n\n"
        
        response += f"💡 Chain Strategy: Tailor approach per location while leveraging chain relationship for volume opportunities."
        
        return response
    
    def _normalize_account_name(self, name: str) -> str:
        """Normalize account names for lookup"""
        name_lower = name.lower()
        
        # Handle specific account name variations
        if "spiga" in name_lower:
            return "spiga"
        elif "barcelona" in name_lower:
            if "norwalk" in name_lower or "waypointe" in name_lower:
                return "barcelona_norwalk"
            elif "fairfield" in name_lower:
                return "barcelona_fairfield"
            else:
                return "barcelona_norwalk"  # Default to Norwalk
        elif "elm" in name_lower:
            return "elm"
        elif "cottage" in name_lower:
            return "the_cottage"
        elif "bin" in name_lower and ("100" in name_lower or "hundred" in name_lower):
            return "bin_100"
        elif "blackstones" in name_lower or "blackstone" in name_lower:
            if "grille" in name_lower or "southport" in name_lower:
                return "blackstones_grille"
            elif "norwalk" in name_lower:
                return "blackstones_norwalk"
            elif "stamford" in name_lower:
                return "blackstones_stamford"
            else:
                return "blackstones_grille"  # Default to Grille
        elif "rebecca" in name_lower:
            return "rebeccas"
        elif "99" in name_lower and "bottle" in name_lower:
            return "99_bottles"
        elif "horseneck" in name_lower or "horse neck" in name_lower:
            return "horseneck"
        elif "db" in name_lower and "fine" in name_lower:
            return "db_fine_wines"
        elif "greens" in name_lower and "farm" in name_lower:
            return "greens_farms"
        elif "labella" in name_lower or "la bella" in name_lower:
            return "labellas"
        elif "acme" in name_lower:
            return "acme_liquors"
        
        return name_lower.replace(" ", "_").replace("-", "_")
    
    def _suggest_accounts(self, requested_name: str) -> str:
        """Suggest available accounts when lookup fails"""
        restaurants = [acc for acc in self.tactical_briefings.values() if acc['type'] == 'restaurant']
        retail = [acc for acc in self.tactical_briefings.values() if acc['type'] == 'retail']
        
        response = f"Account '{requested_name}' not found.\n\n"
        response += f"🍽️ RESTAURANTS ({len(restaurants)}):\n"
        for acc in restaurants[:5]:  # Show first 5
            response += f"   • {acc['name']} - {acc['location']}\n"
        
        response += f"\n🏪 RETAIL ({len(retail)}):\n"
        for acc in retail[:5]:  # Show first 5
            response += f"   • {acc['name']} - {acc['location']}\n"
        
        response += f"\n💡 Try: 'Brief me on Barcelona' or 'New Canaan accounts'"
        
        return response
    
    def get_distributor_intelligence(self) -> str:
        """Get distributor landscape overview"""
        response = "🏢 Connecticut Distributor Intelligence:\n\n"
        
        for dist_key, dist in self.distributors.items():
            response += f"▪️ {dist['name']}\n"
            response += f"   Coverage: {dist['coverage']}\n"
            response += f"   Specialties: {', '.join(dist['specialties'])}\n"
            response += f"   Status: {dist['relationship_status']}\n"
            response += f"   Recent: {dist['recent_activity']}\n\n"
        
        response += "🎯 Strategic insight: CDI/Breakthru for volume, Martignetti for fine wine, Murphy for quick turns, Missing Link for natural/boutique."
        
        return response
    
    def handle_market_analysis(self) -> str:
        """Provide market analysis and trends"""
        response = "📈 Fairfield County Wine Market Analysis:\n\n"
        response += "🔥 Hot Trends:\n"
        response += "   • Natural wines up 40% at premium accounts\n"
        response += "   • Spanish wines gaining ground (Barcelona effect)\n"
        response += "   • Exclusive allocations driving loyalty\n"
        response += "   • Terroir-driven stories winning over ratings\n\n"
        
        response += "💰 Opportunity Size:\n"
        response += "   • Total pipeline: $3.5M+ annually across 17 accounts\n"
        response += "   • Premium segment growing 25% YoY\n"
        response += "   • Average restaurant: $600K | Average retail: $300K\n\n"
        
        response += "🎯 Tactical Moves:\n"
        response += "   • Barcelona: Spanish portfolio expansion\n"
        response += "   • ELM/Cottage: Burgundy and terroir focus\n" 
        response += "   • Horseneck/DB: Ultra-premium allocations\n"
        response += "   • Blackstones: Prestige with differentiation\n\n"
        
        response += "⚡ Execute fast: Competition heating up on premium allocations. Your edge is speed and story."
        
        return response

# Global instance
fairfield_intelligence = FairfieldCountyIntelligence()

# Handler functions for integration
def handle_customer_briefing(customer_name: str) -> str:
    """Handle customer briefing requests"""
    return fairfield_intelligence.get_tactical_briefing(customer_name)

def handle_voice_briefing(customer_name: str) -> str:
    """Handle voice-optimized customer briefing requests"""
    return fairfield_intelligence.get_voice_briefing(customer_name)

def handle_daily_priorities() -> str:
    """Handle daily priorities requests"""
    return fairfield_intelligence.get_daily_priorities()

def handle_distributor_query() -> str:
    """Handle distributor information requests"""
    return fairfield_intelligence.get_distributor_intelligence()

def handle_market_analysis() -> str:
    """Handle market analysis requests"""
    return fairfield_intelligence.handle_market_analysis()

def handle_regional_briefing(region: str) -> str:
    """Handle regional briefing requests"""
    return fairfield_intelligence.get_regional_briefing(region)

def handle_multi_location_briefing(chain: str) -> str:
    """Handle multi-location briefing requests"""
    return fairfield_intelligence.get_multi_location_briefing(chain)

def get_customer_intelligence(query: str) -> str:
    """Main dispatcher for customer intelligence queries"""
    query_lower = query.lower()
    
    # Voice briefing requests (optimized for TTS)
    if "brief me on" in query_lower or "tell me about" in query_lower:
        # Extract account name after "brief me on" or "tell me about"
        for phrase in ["brief me on ", "tell me about "]:
            if phrase in query_lower:
                account_name = query_lower.split(phrase)[1].strip()
                return handle_voice_briefing(account_name)
    
    # Multi-location requests
    if any(phrase in query_lower for phrase in ["all blackstones", "blackstones locations", "blackstone locations"]):
        return handle_multi_location_briefing("blackstones")
    elif any(phrase in query_lower for phrase in ["all barcelona", "barcelona locations", "both barcelona"]):
        return handle_multi_location_briefing("barcelona")
    
    # Regional briefing requests
    if any(phrase in query_lower for phrase in ["new canaan accounts", "new canaan play", "new canaan rundown"]):
        return handle_regional_briefing("new canaan")
    elif any(phrase in query_lower for phrase in ["westport accounts", "westport play", "westport rundown"]):
        return handle_regional_briefing("westport")
    elif any(phrase in query_lower for phrase in ["norwalk accounts", "norwalk play"]):
        return handle_regional_briefing("norwalk")
    elif any(phrase in query_lower for phrase in ["fairfield accounts", "fairfield play"]):
        return handle_regional_briefing("fairfield")
    elif any(phrase in query_lower for phrase in ["stamford accounts", "stamford play"]):
        return handle_regional_briefing("stamford")
    elif any(phrase in query_lower for phrase in ["greenwich accounts", "greenwich play"]):
        return handle_regional_briefing("greenwich")
    
    # Individual account briefings - more comprehensive matching
    account_keywords = {
        "spiga": ["spiga"],
        "barcelona_norwalk": ["barcelona norwalk", "barcelona waypointe"],
        "barcelona_fairfield": ["barcelona fairfield"],
        "elm": ["elm"],
        "the_cottage": ["cottage", "the cottage"],
        "bin_100": ["bin 100", "bin hundred"],
        "blackstones_grille": ["blackstones grille", "blackstone grille", "grille"],
        "blackstones_norwalk": ["blackstones norwalk", "blackstone norwalk"],
        "blackstones_stamford": ["blackstones stamford", "blackstone stamford"],
        "rebeccas": ["rebecca", "rebeccas"],
        "99_bottles": ["99 bottles", "ninety nine bottles"],
        "horseneck": ["horseneck", "horse neck"],
        "db_fine_wines": ["db fine wines", "db fine wine"],
        "greens_farms": ["greens farms", "green farms"],
        "labellas": ["labellas", "la bellas", "labella"],
        "acme_liquors": ["acme", "acme liquors"]
    }
    
    for account_key, keywords in account_keywords.items():
        if any(keyword in query_lower for keyword in keywords):
            return handle_voice_briefing(account_key)
    
    # Daily priorities and briefings
    if any(phrase in query_lower for phrase in ["focus today", "priorities", "what should i", "daily", "briefing"]):
        return handle_daily_priorities()
    
    # Distributor queries
    if any(word in query_lower for word in ["distributor", "cdi", "martignetti", "murphy", "missing link"]):
        return handle_distributor_query()
    
    # Market analysis
    if any(word in query_lower for word in ["market", "trends", "analysis", "opportunity"]):
        return handle_market_analysis()
    
    # Gap analysis
    if "gap" in query_lower or ("missing" in query_lower and "wine list" in query_lower):
        if "barcelona" in query_lower:
            if "norwalk" in query_lower:
                return "Barcelona Norwalk gaps: rare Rioja, super-premium Cava, micro-lot naturals. Heavy Spanish influence, strong on biodynamic. Lead with depth and exclusivity."
            else:
                return "Barcelona Fairfield gaps: rare vintage Spanish wines, rosé program growth, private label opportunities. Wine and Swine events create experiential potential."
        elif "bin 100" in query_lower:
            return "Bin 100 gaps: minimal natural wines, limited grower Champagne, room for Loire whites and German Rieslings. Hosts multi-course wine dinners with boutique producers."
        elif "spiga" in query_lower:
            return "Spiga gaps: Need exclusive Italian allocations for ultra-wealthy New Canaan clientele. Focus on pairing dinners and private cellar curation. Bring prestige."
        elif "elm" in query_lower:
            return "ELM gaps: no natural wines, limited grower Champagne, room for Loire and German whites. Sophisticated crowd expects terroir-driven, small-lot finds."
        elif "cottage" in query_lower:
            return "The Cottage gaps: limited biodynamic and natural wines, space for rare allocations. Ten Year Tasting menu perfect for pairing collaborations."
        else:
            return "I can analyze wine list gaps for any of our 17 accounts including Barcelona, Spiga, ELM, The Cottage, Bin 100, and others. Which account?"
    
    # Competitive intelligence
    if "compete" in query_lower or "competitor" in query_lower or "beat" in query_lower:
        return "Competitive edge: You move faster than Wine Warehouse, have better relationships than Costco, offer premium allocations they can't. Lead with exclusivity, terroir stories, and service speed. Strike clean."
    
    # Opportunity analysis
    if "opportunity" in query_lower:
        if "barcelona" in query_lower:
            return "Barcelona opportunity: Norwalk 1M+ account with Spanish focus, Fairfield 1M flagship with event potential. Both need rare Spanish, natural wines, premium allocations."
        elif "spiga" in query_lower:
            return "Spiga opportunity: 400K-600K ultra-wealthy New Canaan. Dan Camporeale expects deep knowledge. Lead with exclusive Italian allocations, pairing dinners, private cellar curation."
        elif "elm" in query_lower:
            return "ELM opportunity: 500K-700K refined New American, Chef Luke Venner. Cool-climate Old World focus. Hosts boutique wine dinners. Lead with terroir-driven, small-lot finds."
        else:
            return "Premium opportunities across all 17 accounts. Total pipeline 3.5M+. Specify account for detailed opportunity analysis."
    
    # Tactical briefing requests
    if "tactical" in query_lower:
        if "spiga" in query_lower:
            return handle_customer_briefing("spiga")
        elif "barcelona" in query_lower:
            return handle_customer_briefing("barcelona")
        else:
            return "Tactical briefings available for all 17 accounts. Which account needs tactical intelligence?"
    
    # Default fallback with comprehensive account list
    return "🎯 Aimee Fairfield County Intelligence Ready. 17 premium accounts loaded:\n\n🍽️ RESTAURANTS: Barcelona (2 locations), Spiga, ELM, The Cottage, Bin 100, Blackstones (3 locations), Rebecca's\n\n🏪 RETAIL: Horseneck, DB Fine Wines, 99 Bottles, Greens Farms, LaBella's, Acme\n\n💡 Commands: 'Brief me on [account]', '[Region] accounts', 'Daily priorities', 'Market analysis'\n\nWhich intelligence do you need?"

# Test the system
if __name__ == "__main__":
    print("=== ENHANCED FAIRFIELD COUNTY INTELLIGENCE TEST ===")
    
    test_queries = [
        "Brief me on Spiga",
        "Brief me on Barcelona Norwalk",
        "New Canaan accounts",
        "All Blackstones locations",
        "What should I focus on today?",
        "Tell me about distributors",
        "Market analysis"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("Response:", get_customer_intelligence(query))
        print("-" * 50)