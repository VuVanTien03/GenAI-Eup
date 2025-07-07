import os
import pandas as pd


class DataTransformer:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.csv_dir = os.path.join(base_dir, "csv")
        self.output_dir = os.path.join(base_dir, "processed_csv")
        os.makedirs(self.output_dir, exist_ok=True)

    def process_csv_files(self):
        """Duyệt qua các thư mục con trong `csv_dir` để xử lý các file CSV."""
        for category in os.listdir(self.csv_dir):
            category_path = os.path.join(self.csv_dir, category)
            if not os.path.isdir(category_path):
                continue

            for target_folder in os.listdir(category_path):
                target_path = os.path.join(category_path, target_folder)
                if os.path.isdir(target_path):
                    self.process_target_folder(target_path, category)

    def process_target_folder(self, folder_path: str, category: str):
        """Xử lý tất cả các file CSV trong một thư mục cụ thể."""
        target_name = os.path.basename(folder_path).replace("_csv", "")

        for file in os.listdir(folder_path):
            if file.endswith(".csv"):
                file_path = os.path.join(folder_path, file)
                self.process_csv_file(file_path, target_name, category, file)

    def process_csv_file(self, file_path: str, target_name: str, category: str, original_filename: str):
        """Đọc file CSV, xử lý dữ liệu và lưu kết quả."""
        try:
            df = pd.read_csv(file_path)

            # Thêm cột nếu chưa có
            if "Target" not in df.columns:
                df.insert(0, "Target", target_name)
            if "Category" not in df.columns:
                df.insert(1, "Category", category)

            # Tạo tên file mới
            processed_filename = original_filename.replace(".csv", "_processed.csv")
            output_file = os.path.join(self.output_dir, processed_filename)

            df.to_csv(output_file, index=False)
            print(f"✅ Processed: {output_file}")
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")


if __name__ == "__main__":
    base_dir = "./parsed_data_raw"
    transformer = DataTransformer(base_dir)
    transformer.process_csv_files()
