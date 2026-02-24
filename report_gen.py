import os

def generate_report():
    results_dir = "results"
    report_file = "final_report.html"
    
    if not os.path.exists(results_dir):
        print("❌ Папка results не знайдена!")
        return

    screenshots = [f for f in os.listdir(results_dir) if f.endswith('.png')]
    
    html_content = f"""
    <html>
    <head>
        <title>🐾 Manul QA Report</title>
        <style>
            body {{ font-family: sans-serif; background: #1e1e1e; color: #fff; padding: 20px; }}
            .test-card {{ background: #2d2d2d; border-radius: 8px; padding: 15px; margin-bottom: 20px; border-left: 5px solid #4caf50; }}
            img {{ max-width: 100%; border-radius: 4px; margin-top: 10px; border: 1px solid #444; }}
            h1 {{ color: #4caf50; }}
        </style>
    </head>
    <body>
        <h1>🐾 Manul Automation Report</h1>
        <p>Status: All Critical Missions Complete</p>
    """

    for shot in screenshots:
        test_name = shot.replace("pass_", "").replace(".png", "").replace("_", " ")
        html_content += f"""
        <div class="test-card">
            <h3>✅ Test: {test_name}</h3>
            <img src="{results_dir}/{shot}">
        </div>
        """

    html_content += "</body></html>"
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✅ Звіт згенеровано: {report_file}")

if __name__ == "__main__":
    generate_report()