import json
data = json.load(open('strawberry_response.json', encoding='utf-8'))
for c in data['candidate_summaries']:
    print(f"ID: {c['candidate_id']}")
    print(f"Name: {c['material_name']}, {c.get('total_thickness_um')} um")
    print(f"Status: {c['constraint_status']}")
    print(f"M11 State: {c.get('applicability_state')}")
    print(f"Predicted Shelf Life: {c.get('predicted_shelf_life')}")
    print(f"Evaluation Details: {json.dumps(c.get('evaluation_details'), indent=2)}")
    print("---")
