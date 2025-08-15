import os
import pandas as pd
import json
from collections import defaultdict


class DataTransformer:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.csv_dir = os.path.join(base_dir, "csv")
        self.output_dir = os.path.join(base_dir, "processed_json")
        os.makedirs(self.output_dir, exist_ok=True)

    def process_csv_files(self):
        """Duyệt qua các thư mục con trong `csv_dir` để xử lý các file CSV.
        Trả về danh sách đường dẫn file JSON đã tạo.
        """
        all_outputs = []
        for category in os.listdir(self.csv_dir):
            category_path = os.path.join(self.csv_dir, category)
            if not os.path.isdir(category_path):
                continue

            for target_folder in os.listdir(category_path):
                target_path = os.path.join(category_path, target_folder)
                if os.path.isdir(target_path):
                    outputs = self.process_target_folder(target_path, category)
                    if outputs:
                        all_outputs.extend(outputs)
        return all_outputs

    def process_target_folder(self, folder_path: str, category: str):
        """Xử lý tất cả các file CSV trong một thư mục cụ thể.
        Trả về danh sách đường dẫn file JSON đã tạo.
        """
        target_name = os.path.basename(folder_path).replace("_csv", "")
        outputs = []

        for file in os.listdir(folder_path):
            if file.endswith(".csv"):
                file_path = os.path.join(folder_path, file)
                out = self.process_csv_file(file_path, target_name, category, file)
                if out:
                    outputs.append(out)
        return outputs

    def process_csv_file(self, file_path: str, target_name: str, category: str, original_filename: str):
        """Đọc file CSV, xử lý dữ liệu và lưu kết quả dưới dạng JSON phân cấp."""
        try:
            df = pd.read_csv(file_path)

            # Thêm cột nếu chưa có
            if "Target" not in df.columns:
                df.insert(0, "Target", target_name)
            if "Category" not in df.columns:
                df.insert(1, "Category", category)

            # Tạo mapping phân cấp
            skills_map = defaultdict(list)
            subskills_map = defaultdict(list)
            subsubskills_map = defaultdict(list)

            for _, row in df.iterrows():
                key = (row['Group'], row['Parent'])
                item = row['Skill']
                if row['Type'] == 'Skill':
                    skills_map[key].append(item)
                elif row['Type'] == 'Sub-skill':
                    subskills_map[key].append(item)
                elif row['Type'] == 'Sub-sub-skill':
                    subsubskills_map[key].append(item)

            # Hàm dựng cây phân cấp
            def build_structure(group, parent):
                result = []
                for skill in skills_map.get((group, parent), []):
                    skill_entry = {
                        "name": skill,
                        "subskills": []
                    }

                    for subskill in subskills_map.get((group, skill), []):
                        subskill_entry = {
                            "name": subskill,
                            "subsubskills": subsubskills_map.get((group, subskill), [])
                        }
                        skill_entry["subskills"].append(subskill_entry)

                    result.append(skill_entry)
                return result

            # Xây JSON đầu ra
            results = []
            targets_df = df[df["Type"] == "Target"]
            for _, row in targets_df.iterrows():
                group = row["Group"]
                target = row["Skill"]
                entry = {
                    "target": target,
                    "category": category,
                    "skills": build_structure(group, target)
                }
                results.append(entry)

            # Lưu file JSON
            processed_filename = original_filename.replace(".csv", ".json")
            output_file = os.path.join(self.output_dir, processed_filename)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            print(f"✅ Created hierarchy JSON: {output_file}")
            return output_file
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return None

if __name__ == "__main__":
    base_dir = "./parsed_data_raw"
    transformer = DataTransformer(base_dir)
    out = transformer.process_csv_files()
    print(out)
