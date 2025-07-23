import os
from bs4 import BeautifulSoup
import pandas as pd

class PageParser:
    def __init__(self, file_path, output_dir="parsed_data_raw/csv/roadmap/backend_csv"):
        self.file_path = file_path
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def parse_and_save_skills(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")

        # SVG roadmap kỹ năng thường nằm trong <svg> <text>
        nodes = soup.select("svg text")
        all_lines = [node.get_text(strip=True) for node in nodes if node.get_text(strip=True)]

        skills_data = []
        current_parent = None
        current_group = "Frontend"

        # Các từ khóa gợi ý kỹ năng chính
        main_keywords = [
            "Front-end", "Internet", "HTML", "CSS", "JavaScript", "Git", "GitHub", "Tailwind", "React", "Vue.js",
            "Testing", "Build Tools", "Authentication Strategies", "TypeScript", "SSR", "GraphQL",
            "Static Site Generators", "PWAs", "Mobile Apps", "Desktop Apps", "Performance Metrics", "Browser APIs"
        ]

        for line in all_lines:
            line = line.strip()

            if not line:
                continue

            # Nếu là kỹ năng chính / nhóm lớn
            if line in main_keywords:
                current_parent = line
                skill_type = "Category"
                skills_data.append({
                    "Skill": line,
                    "Parent": None,
                    "Group": current_group,
                    "Type": skill_type
                })
                continue

            # Nếu là câu hỏi hoặc mô tả
            if "?" in line or line.lower().startswith("what is"):
                skill_type = "Question"
            elif len(line.split()) <= 2:
                skill_type = "Keyword"
            else:
                skill_type = "Sub-skill"

            skills_data.append({
                "Skill": line,
                "Parent": current_parent,
                "Group": current_group,
                "Type": skill_type
            })

        # Lưu ra file CSV có cấu trúc
        df = pd.DataFrame(skills_data)
        filename = os.path.basename(self.file_path).replace(".html", ".csv")
        save_path = os.path.join(self.output_dir, filename)
        df.to_csv(save_path, index=False, encoding="utf-8-sig")
        print(f"✅ Đã lưu kỹ năng có phân cấp vào: {save_path}")


if __name__ == "__main__":
    file_path = "html_pages/roadmap/backend/backend.html"
    parser = PageParser(file_path)
    print("_____________Start Parse______________________")
    parser.parse_and_save_skills()