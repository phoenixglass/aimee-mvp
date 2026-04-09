from aimee_wine_intelligence import AimeeWineIntelligence, handle_taste_query, handle_pairing_query

wine_intel = AimeeWineIntelligence()

print("=== Testing Wine Intelligence ===")
print("1. Taste Query Test:")
result1 = handle_taste_query(['fruity'], wine_intel)
print(result1)

print("\n2. Food Pairing Test:")
result2 = handle_pairing_query('seafood', wine_intel)
print(result2)

print("\n3. Celebration Test:")
result3 = handle_pairing_query('celebration', wine_intel)
print(result3)
