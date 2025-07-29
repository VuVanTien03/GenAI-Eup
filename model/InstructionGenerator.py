import os
import json

class InstructionGenerator:
    def __init__(self, input_dir, output_file):
        self.input_dir = input_dir
        self.output_file = output_file
        self.instructions = []

    def generate_all(self):
        # Duyệt qua toàn bộ file trong thư mục
        for filename in os.listdir(self.input_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(self.input_dir, filename)
                self._process_file(file_path)
        self._save_output()

    def _process_file(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for roadmap in data:
            target = roadmap["target"]
            skills = roadmap["skills"]

            # Câu hỏi 1: tổng kỹ năng
            skill_names = [s["name"] for s in skills]
            self._add_pair(
                f"Tôi muốn trở thành {target}. Tôi nên học những kỹ năng nào?",
                ", ".join(skill_names)
            )

            for skill in skills:
                skill_name = skill["name"]
                subskills = skill.get("subskills", [])

                subskill_names = [s["name"] for s in subskills]
                if subskill_names:
                    self._add_pair(
                        f"{skill_name} gồm những kỹ năng con nào?",
                        ", ".join(subskill_names)
                    )

                for subskill in subskills:
                    subskill_name = subskill["name"]
                    subsubskills = subskill.get("subsubskills", [])
                    if subsubskills:
                        self._add_pair(
                            f"Muốn học {subskill_name} thì cần biết những gì?",
                            ", ".join(subsubskills)
                        )
                        self._add_pair(
                            f"{subskill_name} bao gồm những kỹ thuật nào?",
                            ", ".join(subsubskills)
                        )

    def _add_pair(self, instruction, output):
        self.instructions.append({
            "instruction": instruction,
            "input": "",
            "output": output
        })

    def _save_output(self):
        with open(self.output_file, "w", encoding="utf-8") as f:
            for item in self.instructions:
                json.dump(item, f, ensure_ascii=False)
                f.write("\n")
        print(f"✅ Đã sinh {len(self.instructions)} cặp instruction-response và lưu tại: {self.output_file}")


def main():
    input_dir = "../roadmap_crawler/parsed_data_raw/processed_json"
    output_file = "../roadmap_crawler/parsed_data_raw/ai_roadmap_finetune.jsonl"

    generator = InstructionGenerator(input_dir, output_file)
    generator.generate_all()

if __name__ == "__main__":
    main()
