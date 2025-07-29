import json
import torch
from transformers import (
    AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer,
    DataCollatorForLanguageModeling
)
from datasets import load_dataset
from peft import (
    prepare_model_for_kbit_training, get_peft_model, LoraConfig, TaskType
)

class TinyLlamaFineTuner:
    def __init__(self,
                 model_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                 data_path="../roadmap_crawler/parsed_data_raw/ai_roadmap_finetune.jsonl",
                 output_dir="finetuned_tinyllama",
                 max_length=512,
                 auto_convert=True):
        self.model_id = model_id
        self.data_path = data_path
        self.output_dir = output_dir
        self.max_length = max_length
        self.auto_convert = auto_convert
        self.converted_data_path = "converted_train.jsonl"  # file trung gian nếu cần convert

        self.tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=True)
        self.tokenizer.pad_token = self.tokenizer.eos_token

        if self.auto_convert:
            self.convert_instruction_data()

    def convert_instruction_data(self):
        """Chuyển định dạng instruction-style sang prompt/response nếu cần"""
        with open(self.data_path, "r", encoding="utf-8") as infile:
            lines = infile.readlines()

        converted = []
        for line in lines:
            obj = json.loads(line)
            if "instruction" in obj and "output" in obj:
                instruction = obj.get("instruction", "").strip()
                input_text = obj.get("input", "").strip()
                output = obj["output"].strip()

                # Nếu có phần input thì nối vào sau instruction
                prompt = f"{instruction}\n{input_text}" if input_text else instruction
                converted.append({"prompt": prompt, "response": output})
            elif "prompt" in obj and "response" in obj:
                # Nếu đã đúng định dạng thì giữ nguyên
                converted.append(obj)
            else:
                print("⚠️ Dòng không đúng định dạng:", obj)

        # Ghi ra file trung gian
        with open(self.converted_data_path, "w", encoding="utf-8") as out:
            for item in converted:
                out.write(json.dumps(item, ensure_ascii=False) + "\n")

        self.data_path = self.converted_data_path
        print(f"✅ Đã chuyển dữ liệu về định dạng prompt/response: {self.data_path}")

    def load_data(self):
        print("📥 Loading dataset...")
        dataset = load_dataset("json", data_files=self.data_path)["train"]
        return dataset

    def tokenize_data(self, dataset):
        print("🔧 Tokenizing dataset...")

        def tokenize(example):
            prompt = f"<|user|>\n{example['prompt']}\n<|assistant|>\n{example['response']}"
            return self.tokenizer(prompt, padding="max_length", truncation=True, max_length=self.max_length)

        return dataset.map(tokenize, remove_columns=["prompt", "response"])

    def setup_model(self):
        print("🧠 Loading base model...")
        model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            load_in_4bit=True,
            device_map="auto"
        )

        print("🔧 Preparing model for LoRA fine-tuning...")
        model = prepare_model_for_kbit_training(model)

        peft_config = LoraConfig(
            r=8,
            lora_alpha=16,
            task_type=TaskType.CAUSAL_LM,
            lora_dropout=0.05,
            bias="none"
        )

        model = get_peft_model(model, peft_config)
        return model

    def train(self, num_train_epochs=3, batch_size=4, grad_accum=4, lr=2e-4, save_steps=100):
        dataset = self.load_data()
        tokenized_dataset = self.tokenize_data(dataset)
        model = self.setup_model()

        print("⚙️ Setting up training arguments...")
        training_args = TrainingArguments(
            output_dir=self.output_dir,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=grad_accum,
            logging_dir="./logs",
            num_train_epochs=num_train_epochs,
            save_total_limit=2,
            save_steps=save_steps,
            learning_rate=lr,
            fp16=True,
            report_to="none"
        )

        data_collator = DataCollatorForLanguageModeling(tokenizer=self.tokenizer, mlm=False)

        print("🚀 Starting training...")
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset,
            tokenizer=self.tokenizer,
            data_collator=data_collator
        )

        trainer.train()
        print("💾 Saving final model...")
        trainer.save_model(self.output_dir)
        print("✅ Training complete and model saved.")

    def infer(self, prompt, max_new_tokens=100, temperature=0.7):
        print("🤖 Loading fine-tuned model for inference...")
        model = AutoModelForCausalLM.from_pretrained(
            self.output_dir,
            device_map="auto",
            torch_dtype=torch.float16
        )
        model.eval()

        prompt_wrapped = f"<|user|>\n{prompt}\n<|assistant|>\n"
        inputs = self.tokenizer(prompt_wrapped, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        result = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Loại phần prompt khỏi kết quả
        response = result.split("<|assistant|>\n")[-1].strip()
        print("📤 Model output:", response)
        return response
