import psycopg2
import json

def clean_float_values(obj):
    """Recursively convert float values like 3.0 to int 3 in any JSON structure."""
    if isinstance(obj, dict):
        return {k: clean_float_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_float_values(item) for item in obj]
    elif isinstance(obj, float):
        return int(obj) if obj.is_integer() else obj
    elif isinstance(obj, str):
        try:
            f = float(obj)
            return int(f) if f.is_integer() else f
        except:
            return obj
    else:
        return obj

def remove_keys_from_nested_sections(data, keys_to_remove):
    """Remove specified keys from group and link sections only."""
    for item in data:
        if "Group" in item:
            item["Group"] = [
                {k: v for k, v in g.items() if k not in keys_to_remove}
                for g in item["Group"]
            ]
        if "Link" in item:
            item["Link"] = [
                {k: v for k, v in l.items() if k not in keys_to_remove}
                for l in item["Link"]
            ]
    return data

def generate_json_from_master(db_config, master_table, group_table, link_table, output_json_path):
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    # Load all tables
    cur.execute(f'SELECT * FROM "{master_table}";')
    master_rows = cur.fetchall()
    master_cols = [desc[0] for desc in cur.description]

    cur.execute(f'SELECT * FROM "{group_table}";')
    group_rows = cur.fetchall()
    group_cols = [desc[0] for desc in cur.description]

    cur.execute(f'SELECT * FROM "{link_table}";')
    link_rows = cur.fetchall()
    link_cols = [desc[0] for desc in cur.description]

    result = []

    for row in master_rows:
        row_dict = dict(zip(master_cols, row))

        # Normalize Type
        type_value = str(row_dict.get("Type") or "").strip().lower()

        # Enrich with group or link data
        if type_value == "group":
            group_id = row_dict.get("groupid")
            group_items = [
                dict(zip(group_cols, g_row))
                for g_row in group_rows
                if str(g_row[group_cols.index("groupid")]) == str(group_id)
            ]
            row_dict["Group"] = group_items

        elif type_value == "link":
            link_id = row_dict.get("linkid")
            link_items = [
                dict(zip(link_cols, l_row))
                for l_row in link_rows
                if str(l_row[link_cols.index("linkid")]) == str(link_id)
            ]
            row_dict["Link"] = link_items

        result.append(row_dict)

    # Step 1: Clean float values
    result = clean_float_values(result)

    # Step 2: Remove unwanted keys from group/link sections
    keys_to_remove = ["groupid", "setid", "document_type", "linkid"]
    result = remove_keys_from_nested_sections(result, keys_to_remove)

    # Save to JSON file
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    cur.close()
    conn.close()
    print(f"✅ JSON file saved to: {output_json_path}")

# Example usage
db_config = {
    'host': 'localhost',
    'port': '5432',
    'dbname': 'Set-2',
    'user': 'postgres',
    'password': 'Janan!1802'
}

generate_json_from_master(
    db_config,
    master_table='Master_Input_JSON_Table',
    group_table='Group_Table',
    link_table='Link_Table',
    output_json_path='Enriched_Master_Input_JSON.json'
)
