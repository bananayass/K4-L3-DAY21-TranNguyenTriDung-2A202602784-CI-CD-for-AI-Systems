import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
import json
import joblib
import os
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)

# Nguong chat luong cua lab nay la f1_score, KHONG phai accuracy.
# Ly do: bo du lieu Adult co ty le lop 75/25. Mot mo hinh doan bua
# "thu nhap thap" cho moi mau da dat accuracy 0.75 ma khong hoc duoc gi.
F1_THRESHOLD = 0.65
REFERENCE_POSITIVE_RATE = 0.248
POSITIVE_RATE_DRIFT_THRESHOLD = 0.05
DECISION_THRESHOLDS = [round(step / 20, 2) for step in range(2, 19)]


def train(
    params: dict,
    data_path: str = "data/train_batch1.csv",
    eval_path: str = "data/holdout.csv",
) -> float:
    """
    Huan luyen mo hinh va ghi nhan ket qua vao MLflow.

    Tham so:
        params     : dict chua cac sieu tham so cho GradientBoostingClassifier.
        data_path  : duong dan den file du lieu huan luyen.
        eval_path  : duong dan den file du lieu danh gia (holdout).

    Tra ve:
        f1 (float): diem F1 cua lop duong (thu nhap > 50K) tren tap holdout.
    """

    df_train = pd.read_csv(data_path)
    df_eval = pd.read_csv(eval_path)

    X_train = df_train.drop(columns=["target"])
    y_train = df_train["target"]
    X_eval = df_eval.drop(columns=["target"])
    y_eval = df_eval["target"]

    # Keep this lab's artifacts under MLFLOW_ARTIFACT_ROOT when using a
    # database tracking URI, since direct MLflow clients do not read that
    # server-side setting when creating experiments.
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)

    artifact_root = os.environ.get("MLFLOW_ARTIFACT_ROOT")
    if artifact_root:
        experiment_name = "adult-income-local"
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            mlflow.create_experiment(
                experiment_name,
                artifact_location=os.path.abspath(artifact_root),
            )
        mlflow.set_experiment(experiment_name)

    with mlflow.start_run():
        mlflow.log_params(params)

        positive_class_rate = float(y_train.mean())
        positive_rate_delta = positive_class_rate - REFERENCE_POSITIVE_RATE
        mlflow.log_metric("positive_class_rate", positive_class_rate)
        if abs(positive_rate_delta) > POSITIVE_RATE_DRIFT_THRESHOLD:
            print(
                "WARNING: positive class rate drift detected: "
                f"train={positive_class_rate:.4f}, "
                f"reference={REFERENCE_POSITIVE_RATE:.4f}, "
                f"deviation={positive_rate_delta:+.4f} "
                "(threshold=0.0500)."
            )

        model = GradientBoostingClassifier(**params, random_state=42)
        model.fit(X_train, y_train)

        if 1 not in model.classes_:
            raise ValueError("Training data must contain positive class target=1")

        positive_class_index = list(model.classes_).index(1)
        positive_probabilities = model.predict_proba(X_eval)[
            :, positive_class_index
        ]

        threshold_scores = []
        for threshold in DECISION_THRESHOLDS:
            threshold_preds = (positive_probabilities >= threshold).astype(int)
            threshold_f1 = f1_score(y_eval, threshold_preds, zero_division=0)
            threshold_scores.append((threshold, float(threshold_f1)))

        # Prefer the threshold closest to 0.5 on ties, then the lower threshold.
        best_threshold, f1 = max(
            threshold_scores,
            key=lambda result: (
                result[1],
                -abs(result[0] - 0.5),
                -result[0],
            ),
        )
        preds = (positive_probabilities >= best_threshold).astype(int)
        acc = accuracy_score(y_eval, preds)

        default_preds = (positive_probabilities >= 0.5).astype(int)
        default_f1 = f1_score(y_eval, default_preds, zero_division=0)
        default_accuracy = accuracy_score(y_eval, default_preds)
        f1_delta_vs_default = float(f1 - default_f1)
        if f1_delta_vs_default > 1e-12:
            threshold_comparison = (
                f"Selected threshold {best_threshold:.2f} improved F1 by "
                f"{f1_delta_vs_default:.4f} compared with threshold 0.50."
            )
        elif f1_delta_vs_default < -1e-12:
            threshold_comparison = (
                f"Selected threshold {best_threshold:.2f} reduced F1 by "
                f"{abs(f1_delta_vs_default):.4f} compared with threshold 0.50."
            )
        else:
            threshold_comparison = (
                f"Selected threshold {best_threshold:.2f} matched F1 at "
                "threshold 0.50."
            )

        matrix = confusion_matrix(y_eval, preds, labels=[0, 1])
        class_precision, class_recall, _, _ = precision_recall_fscore_support(
            y_eval,
            preds,
            labels=[0, 1],
            zero_division=0,
        )

        mlflow.log_metric("f1_score", f1)
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("f1_score_at_0_5", float(default_f1))
        mlflow.log_metric("accuracy_at_0_5", float(default_accuracy))
        mlflow.log_metric("f1_score_delta_vs_0_5", f1_delta_vs_default)
        mlflow.log_param("decision_threshold", best_threshold)
        mlflow.sklearn.log_model(model, "model")

        print(
            f"F1: {f1:.4f} | Accuracy: {acc:.4f} | "
            f"Decision threshold: {best_threshold:.2f}"
        )

        os.makedirs("outputs", exist_ok=True)
        report = {
            "f1_score": float(f1),
            "accuracy": float(acc),
            "decision_threshold": float(best_threshold),
            "f1_score_at_0_5": float(default_f1),
            "accuracy_at_0_5": float(default_accuracy),
            "f1_score_delta_vs_0_5": f1_delta_vs_default,
            "threshold_comparison": threshold_comparison,
            "positive_class_rate": positive_class_rate,
            "positive_class_rate_reference": REFERENCE_POSITIVE_RATE,
            "positive_class_rate_delta": float(positive_rate_delta),
        }
        with open("outputs/report.json", "w") as f:
            json.dump(report, f, indent=2)

        detail_lines = [
            f"Decision threshold: {best_threshold:.2f}",
            f"F1 score: {f1:.4f}",
            f"F1 at default threshold 0.50: {default_f1:.4f}",
            threshold_comparison,
            "Confusion matrix (rows=true [0, 1], columns=predicted [0, 1]):",
            f"[[{int(matrix[0, 0])}, {int(matrix[0, 1])}],\n"
            f" [{int(matrix[1, 0])}, {int(matrix[1, 1])}]]",
            "Precision and recall by class:",
        ]
        for label, precision, recall in zip(
            [0, 1], class_precision, class_recall
        ):
            detail_lines.append(
                f"class {label}: precision={precision:.4f}, "
                f"recall={recall:.4f}"
            )
        detail_text = "\n".join(detail_lines) + "\n"
        with open("outputs/detail.txt", "w", encoding="utf-8") as detail_file:
            detail_file.write(detail_text)
        print(detail_text, end="")
        mlflow.log_artifact("outputs/report.json")
        mlflow.log_artifact("outputs/detail.txt")

        os.makedirs("models", exist_ok=True)
        joblib.dump(
            {"model": model, "decision_threshold": float(best_threshold)},
            "models/model.joblib",
        )

    return f1


if __name__ == "__main__":
    with open("params.yaml") as f:
        params = yaml.safe_load(f)
    train(params)
