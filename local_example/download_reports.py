"""Download AEO reports for buildalab from Supabase."""

import os

from supabase import create_client

REPORT_IDS = [
    "f32a4caf-c1ef-4c1b-aa35-0151b818347e",  # chatgpt
    "b73638fb-c56b-4f23-ba97-efe491db4e10",  # perplexity
]


def main():
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    rows = (
        client.table("prospects_demo")
        .select("id,model,report")
        .eq("prospect_email", "faconchar@gmail.com")
        .in_("id", REPORT_IDS)
        .execute()
    )

    for row in rows.data:
        model = row["model"]
        report_hex = row.get("report")
        if not report_hex:
            print(f"No report for {model}")
            continue

        # Supabase returns bytea as hex-escaped string: \x2550...
        if report_hex.startswith("\\x"):
            hex_str = report_hex[2:]
        else:
            hex_str = report_hex
        pdf_bytes = bytes.fromhex(hex_str)

        filename = f"local_example/buildalab_aeo_report_{model}.pdf"
        with open(filename, "wb") as f:
            f.write(pdf_bytes)
        print(f"Saved: {filename} ({len(pdf_bytes)} bytes)")


if __name__ == "__main__":
    main()
