import os
import glob
import re
import datetime
from query import identify_ancient_person

def run_automated_test(test_folder="data/test_queries"):
    report_lines = []
    
    def log_and_print(text):
        print(text)
        report_lines.append(text)

    log_and_print("🚀 啟動自動化測試管線...")

    extensions = ('*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG')
    test_images = []
    for ext in extensions:
        test_images.extend(glob.glob(os.path.join(test_folder, ext)))

    if not test_images:
        log_and_print(f"❌ 找不到測試圖片，請確保 {test_folder} 資料夾內有圖片！")
        return

    total_tests = len(test_images)
    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0

    log_and_print(f"📊 共找到 {total_tests} 張測試圖片，開始執行比對...\n")
    log_and_print(f"{'圖片檔名':<20}{'正確答案':<10}{'圖片狀態(平均)':<20}{'文獻狀態(平均)':<20}{'最終結果'}")
    log_and_print("-" * 85)

    for img_path in test_images:
        filename = os.path.basename(img_path)
        ground_truth = filename.split('.')[0]

        try:
            system_output = identify_ancient_person(img_path)

            img_status = "未達標 ❌"
            txt_status = "未達標 ❌"

            img_match = re.search(r"🖼️ 圖片群體比對過關.*?平均距離:\s*([0-9.]+)", system_output)
            if img_match:
                img_status = f"達標 ✅ ({img_match.group(1)})"

            txt_match = re.search(r"✅ 文獻群體比對過關.*?平均距離:\s*([0-9.]+)", system_output)
            if txt_match:
                txt_status = f"達標 ✅ ({txt_match.group(1)})"

            img_success_str = f"圖片群體比對過關: {ground_truth}"
            txt_success_str = f"文獻群體比對過關: {ground_truth}"

            if "❌ 圖片比對未達標" in system_output and "❌ 文獻比對未達標" in system_output:
                final_result = "未答 (Unanswered) ⚪"
                unanswered_count += 1
            elif img_success_str in system_output or txt_success_str in system_output:
                final_result = "答對 (Correct) 🎉"
                correct_count += 1
            else:
                final_result = "答錯 (Incorrect) 💥"
                incorrect_count += 1

        except Exception as e:
            img_status = "Error"
            txt_status = "Error"
            final_result = f"錯誤 (Error)"
            unanswered_count += 1

        log_and_print(f"{filename:<20}{ground_truth:<10}{img_status:<20}{txt_status:<20}{final_result}")

    accuracy = (correct_count / total_tests) * 100 if total_tests > 0 else 0
    log_and_print("\n================== 📊 最終測試統計 ==================")
    log_and_print(f"總測試圖片總數 (Total): {total_tests} 張")
    log_and_print(f"答對次數 (Correct)   : {correct_count} 張")
    log_and_print(f"答錯次數 (Incorrect) : {incorrect_count} 張")
    log_and_print(f"未答次數 (Unanswered): {unanswered_count} 張")
    log_and_print(f"🔥 系統總準確率 (Accuracy): {accuracy:.2f}%")
    log_and_print("====================================================")

    # ==========================================
    # 🌟 核心修改：固定檔名，並使用 "a" (附加模式)
    # ==========================================
    report_filename = "data/test_report.txt"
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 🌟 打開檔案時，模式設定為 "a" (append)
    with open(report_filename, "a", encoding="utf-8") as f:
        # 在每次報告開頭加上時間分隔線，這樣同一個檔案裡才看得出是哪次跑的
        f.write(f"\n\n{'='*25} 執行時間: {current_time} {'='*25}\n")
        f.write("\n".join(report_lines))
        f.write("\n") # 在尾巴多加一個換行，讓下一次寫入時保持距離
        
    print(f"\n💾 測試報告已成功【附加】至：{report_filename}")

if __name__ == "__main__":
    run_automated_test()
