import os

# Create templates directory
os.makedirs('templates', exist_ok=True)

# Create tactical_briefing_web.py
with open('tactical_briefing_web.py', 'w') as f:
    f.write('''# [Paste the full tactical_briefing_web.py code here]''')

# Create templates/tactical_dashboard.html
with open('templates/tactical_dashboard.html', 'w') as f:
    f.write('''# [Paste the full HTML code here]''')

print("✅ Files created successfully!")
print("Now run: python tactical_briefing_web.py")