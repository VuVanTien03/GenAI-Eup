from TinyLlamaFineTuner import TinyLlamaFineTuner

finetuner = TinyLlamaFineTuner(
    model_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    data_path="../roadmap_crawler/parsed_data_raw/ai_roadmap_finetune.jsonl",  # file gốc dạng {"instruction": "..."}
    output_dir="finetuned_tinyllama"
)

#finetuner.train(num_train_epochs=3)

# Dùng để test sau khi đã fine-tune xong
test_prompt = "Tôi muốn trở thành frontend developer, cho tôi những kỹ năng cần học"
finetuner.infer(test_prompt)