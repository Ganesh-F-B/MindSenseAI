import json

with open('C:/Users/ganes/.gemini/antigravity/brain/8c3811fe-a6e1-4f58-965b-8945e3ca6f0f/scratch/task5_phase2_calibration_results.json') as f:
    data = json.load(f)

print('=== COMPETING CASES ===')
for r in data['records']:
    if r['pattern'] == 'competing':
        print(f"Category: {r['category']}")
        print(f"  Text: {r['text']}")
        print(f"  Primary: {r['primary']} ({r['primary_confidence']})")
        print(f"  Secondary: {r['secondary']}")
        print(f"  Top2 Conc: {r['top2_concentration']}, Margin: {r['margin']}, RelRatio: {r['relative_ratio']}, TailContrast: {r['tail_contrast']}")
        print()

print('=== BOUNDARY PROXIMITY ===')
for k, v in data['boundary_proximity'].items():
    if k != 'details':
        print(f"{k}: {v}")
    else:
        print("Details of boundary proximities:")
        for bk, bv in v.items():
            if bv:
                print(f"  {bk}:")
                for item in bv:
                    print(f"    {item}")

print()
print("=== CONCENTRATED EXAMPLES IN MIXED / CONTRAST CATEGORIES ===")
for r in data['records']:
    if r['category'] in ['mixed_pos_neg', 'emotional_contrast', 'two_negative', 'temporal_change'] and r['pattern'] == 'concentrated':
        print(f"[{r['category']}] {r['text']}")
        print(f"  Top: {r['primary']} ({r['primary_confidence']})")
        dist_sorted = sorted(r['distribution'].items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"  Top 3 in dist: {dist_sorted}")
