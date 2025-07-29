import os
from bs4 import BeautifulSoup
import pandas as pd

class PageParser:
    def __init__(self, file_path, output_dir, group_name):
        self.file_path = file_path
        self.output_dir = output_dir
        self.group_name = group_name
        os.makedirs(self.output_dir, exist_ok=True)

    def parse_and_save_skills(self):
        from collections import deque

        with open(self.file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")

        nodes = soup.select("[data-type]")
        level_map = {
            "title": 0,
            "label": 1,
            "topic": 2,
            "subtopic": 3
        }

        skills_data = []
        last_seen = [None, None, None, None]

        # ✅ Tạm lưu các sub-sub-skill chưa có parent
        pending_subsub = []

        for node in nodes:
            text = node.get_text(strip=True)
            if not text:
                continue

            data_type = node.get("data-type")
            level = level_map.get(data_type, -1)
            if level == -1:
                continue

            parent = None
            if level > 0:
                # Ưu tiên tìm parent từ last_seen
                for l in range(level - 1, -1, -1):
                    if last_seen[l]:
                        parent = last_seen[l]
                        break

            # Xử lý đặc biệt cho sub-sub-skill
            if level == 3:
                # Chưa biết sub-skill, chờ xử lý sau
                pending_subsub.append({
                    "Skill": text,
                    "Parent": None,  # chưa biết
                    "Group": self.group_name,
                    "Type": "Sub-sub-skill"
                })
            elif level == 2:
                # Gặp sub-skill → gán parent cho pending sub-sub-skills
                for item in pending_subsub:
                    item["Parent"] = text
                    skills_data.append(item)
                pending_subsub = []

                # Ghi sub-skill hiện tại
                skills_data.append({
                    "Skill": text,
                    "Parent": parent,
                    "Group": self.group_name,
                    "Type": "Sub-skill"
                })
            else:
                # Ghi các cấp còn lại (title, skill)
                skills_data.append({
                    "Skill": text,
                    "Parent": parent,
                    "Group": self.group_name,
                    "Type": ["Target", "Skill", "Sub-skill", "Sub-sub-skill"][level]
                })

            # Cập nhật last_seen
            last_seen[level] = text
            for i in range(level + 1, len(last_seen)):
                last_seen[i] = None

        # ✅ Nếu còn sub-sub-skill mà không có sub-skill nào sau đó
        for item in pending_subsub:
            skills_data.append(item)

        # Xuất CSV
        df = pd.DataFrame(skills_data)
        filename = os.path.basename(self.file_path).replace(".html", ".csv")
        save_path = os.path.join(self.output_dir, filename)
        df.to_csv(save_path, index=False, encoding="utf-8-sig")
        print(f"✅ Đã lưu kỹ năng vào: {save_path}")

def parse_all_html_files(input_root="html_pages/roadmap", output_root="parsed_data_raw/csv/roadmap"):
    for root, _, files in os.walk(input_root):
        for file in files:
            if file.endswith(".html"):
                file_path = os.path.join(root, file)

                # Lấy tên thư mục cha làm group name
                group_name = os.path.basename(os.path.dirname(file_path))

                # Tạo thư mục output tương ứng
                output_dir = os.path.join(output_root, f"{group_name}_csv")

                parser = PageParser(file_path, output_dir, group_name)
                print(f"\n📂 Đang xử lý: {file_path}")
                parser.parse_and_save_skills()


if __name__ == "__main__":
    print("🚀 Bắt đầu phân tích toàn bộ file HTML...")
    parse_all_html_files()
    print("✅ Hoàn tất.")
