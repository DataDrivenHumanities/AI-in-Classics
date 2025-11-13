import csv
import pandas as pd

def main():
    # load data from both csv files
    emotionbert_df = pd.read_csv("emotionBert_sentiment.csv")
    greekbert_v2_df = pd.read_csv("greekbert_v2_sentiment.csv")
    # for each line in one dataframe, compare output of the other, create a diff
    total_count = 0
    same_count = 0
    total_greekbert_conf = 0
    total_emotionbert_conf = 0
    total_conf_diff = 0
    totals = []
    diffs = []
    for idx, row in emotionbert_df.iterrows():
        greekbert_row = greekbert_v2_df.iloc[idx]
        total_entry = {
            "sequence": row.sequence,
            "translation": row.translation,
            "emotionbert sentiment": row.sentiment,
            "emotionbert confidence": row.score,
            "greekbert v2 sentiment": greekbert_row.sentiment,
            "greekbert v2 confidence": greekbert_row.score,
            "same sentiment": (row.sentiment == greekbert_row.sentiment),
            "confidence diff (enhanced - original)": (greekbert_row.score - row.score)
        }
        totals.append(total_entry)
        if (row.sentiment != greekbert_row.sentiment):
            diff_entry = {
                "sequence": row.sequence,
                "translation": row.translation,
                "emotionbert sentiment": row.sentiment,
                "emotionbert confidence": row.score,
                "greekbert v2 sentiment": greekbert_row.sentiment,
                "greekbert v2 confidence": greekbert_row.score,
                "confidence diff (enhanced - original)": (greekbert_row.score - row.score)
            }
            diffs.append(diff_entry)

        # calculate  metrics
        total_count += 1
        same_count += 1 if row.sentiment == greekbert_row.sentiment else 0
        total_greekbert_conf += greekbert_row.score
        total_emotionbert_conf += row.score
        total_conf_diff += greekbert_row.score - row.score

    total_fieldnames = ["sequence", "translation", "emotionbert sentiment", "emotionbert confidence",
                        "greekbert v2 sentiment", "greekbert v2 confidence",
                        "same sentiment", "confidence diff (enhanced - original)"]
    diff_fieldnames = ["sequence", "translation", "emotionbert sentiment", "emotionbert confidence",
                  "greekbert v2 sentiment", "greekbert v2 confidence",
                  "confidence diff (enhanced - original)"]

    csv_file_name = "totals.csv"
    diff_file_name = "diffs.csv"

    # write all rows to totals file
    try:
        with open(csv_file_name, 'w', newline='', encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=total_fieldnames)
            writer.writeheader()
            writer.writerows(totals)

        print(f"Successfully wrote data to {csv_file_name}")

    except IOError:
        print(f"I/O error occurred while writing to {csv_file_name}")

    # write different labels to a diff file
    try:
        with open(diff_file_name, 'w', newline='', encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=diff_fieldnames)
            writer.writeheader()
            writer.writerows(diffs)

        print(f"Successfully wrote data to {diff_file_name}")

    except IOError:
        print(f"I/O error occurred while writing to {csv_file_name}")
    # calculate metrics such as percentage of sameness, average confidence of each etc

    # calculate final stats:
    agreement_percent = same_count / total_count * 100
    average_greekbert_conf = total_greekbert_conf / total_count
    average_emotionbert_conf = total_emotionbert_conf / total_count
    average_conf_diff = total_conf_diff / total_count

    print(f"{total_count} phrases and words analyzed. \n\n"
          f"The models agreed on {round(agreement_percent, 2)}% of the labels.\n"
          f"Average GreekBert V2 Model Confidence: {round(average_greekbert_conf, 2)}\n"
          f"Average EmotionBert Model (original) Confidence: {round(average_emotionbert_conf, 2)}\n"
          f"Average Confidence Difference: {round(average_conf_diff, 2)}")

if __name__ == "__main__":
    main()
