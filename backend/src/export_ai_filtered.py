import io
import openpyxl
from flask import Flask, request, send_file, jsonify
import json

app = Flask(__name__)

@app.route('/export-ai-filtered', methods=['POST'])
def export_ai_filtered():
    try:
        data = request.get_json()
        filtered_results = data.get('filtered_results', [])
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "AI Filtered Results"
        # Define the fields as columns (must match your AI prompt fields)
        fields = [
            "Location", "River/Wadi", "Event date", "Event time", "Event duration", "Article date",
            "Flood classification", "Flood depth", "Flood extent", "Rainfall depth", "Casualties/injuries",
            "Damage", "Costs", "Road closures", "Emergency services", "Response services", "Displacement",
            "Affected population", "Return period", "Past events", "Peak Discharge"
        ]
        ws.append(fields)
        for item in filtered_results:
            # If item is a string, try to parse as JSON
            if isinstance(item, str):
                try:
                    item = json.loads(item)
                except Exception:
                    item = {f: '' for f in fields}
            row = [item.get(f, '') for f in fields]
            ws.append(row)
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="ai_filtered_results.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5050, debug=True)
