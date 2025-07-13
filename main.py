import pandas as pd
import psycopg2
import json

def create_table_from_sheet(excel_path, sheet_name, table_name, db_config):
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    df.columns = df.columns.astype(str)

    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    columns = df.columns
    escaped_columns = [f'"{col}"' for col in columns]
    col_defs = ', '.join([f'"{col}" TEXT' for col in columns])
    create_query = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({col_defs});'
    cur.execute(create_query)

    for _, row in df.iterrows():
        values = [str(v) if pd.notnull(v) else None for v in row]
        placeholders = ', '.join(['%s'] * len(values))
        insert_query = f'INSERT INTO "{table_name}" ({", ".join(escaped_columns)}) VALUES ({placeholders});'
        cur.execute(insert_query, values)

    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ Table '{table_name}' created from sheet '{sheet_name}'")

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
        if "group" in item:
            item["group"] = [
                {k: v for k, v in g.items() if k not in keys_to_remove}
                for g in item["group"]
            ]
        if "link" in item:
            item["link"] = [
                {k: v for k, v in l.items() if k not in keys_to_remove}
                for l in item["link"]
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

        # Safely extract and normalize Type
        type_raw = row_dict.get("Type")
        type_value = str(type_raw).strip().lower() if type_raw is not None else ""

        # Enrich with group or link data if applicable
        if type_value == "group":
            group_id = row_dict.get("GroupID")
            group_items = [
                dict(zip(group_cols, g_row))
                for g_row in group_rows
                if str(g_row[group_cols.index("GroupID")]) == str(group_id)
            ]
            row_dict["group"] = group_items

        elif type_value == "link":
            link_id = row_dict.get("LinkID")
            link_items = [
                dict(zip(link_cols, l_row))
                for l_row in link_rows
                if str(l_row[link_cols.index("LinkID")]) == str(link_id)
            ]
            row_dict["link"] = link_items

        # Append enriched or plain row
        result.append(row_dict)

    # Step 1: Clean float values
    result = clean_float_values(result)

    # Step 2: Remove unwanted keys from group/link sections
    keys_to_remove = ["GroupID", "SetID", "Document_Type", "LinkID"]
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

excel_path = 'InputJSON-Set2.xlsx'

# Step 1: Create tables
create_table_from_sheet(excel_path, 'Input JSON', 'Master Input JSON Table', db_config)
create_table_from_sheet(excel_path, 'Group Table', 'Group Table', db_config)
create_table_from_sheet(excel_path, 'Link Table', 'Link Table', db_config)

# Step 2: Generate enriched JSON
generate_json_from_master(
    db_config,
    master_table='Master Input JSON Table',
    group_table='Group Table',
    link_table='Link Table',
    output_json_path='Enriched_Master_Input_JSON.json'
)
