# Báo Cáo Lab Day 21 - CI/CD cho AI Systems

| | |
|---|---|
| Họ và tên | Trần Nguyễn Trí Dũng |
| MSSV | 2A202602784|
| Lớp / Khóa | K4 |
| Repo GitHub | https://github.com/bananayass/K4-L3-DAY21-TranNguyenTriDung-2A202602784-CI-CD-for-AI-Systems |
| Ngày nộp | 07/10/2026|

---

## 1. Bộ Siêu Tham Số Đã Chọn và Lý Do

| Lần chạy | n_estimators | learning_rate | max_depth | f1_score | accuracy |
|---|---|---|---|---|---|
| 1 | 100 | 0.1 | 3 | 0.7109 | 0.878 |
| 2 | 50 | 0.05 | 2 | 0.6051 | 0.846 |
| 3 | 200 | 0.1 | 5 | 0.7149 | 0.874 |

**Bộ siêu tham số đã chọn:** `n_estimators=200`, `learning_rate=0.1`, `max_depth=5`.

**Lý do:** Run 3 có F1 cao nhất (0.7149), vượt ngưỡng 0.65; Run 1 đạt 0.7109 và Run 2 đạt 0.6051. Accuracy cao nhất lại thuộc Run 1 (0.878, so với 0.874), nên chọn theo accuracy sẽ bỏ qua F1 tốt nhất. F1 cân bằng precision và recall của lớp dương `target=1`. Run 3 giữ learning rate 0.1, tăng số cây và độ sâu, giúp F1 tăng 0.004 so với mặc định; Run 2 đổi đồng thời ba tham số nên không thể tách ảnh hưởng riêng của từng tham số.

---

## 2. Vì Sao Ngưỡng Chất Lượng Đặt Trên F1 Chứ Không Phải Accuracy

Adult có 24,8% mẫu thu nhập trên 50.000 USD và 75,2% mẫu thu nhập thấp. Mô hình luôn đoán lớp thấp vẫn đạt accuracy 0,752 nhưng bỏ sót toàn bộ lớp dương. F1 lớp dương là trung bình điều hòa giữa precision (dự đoán thu nhập cao đúng) và recall (tìm được người thu nhập cao), qua đó đo khả năng nhận diện nhóm mà accuracy che khuất. Không dùng `average="weighted"` vì lớp đa số có thể chi phối điểm; `average="macro"` trộn F1 của cả hai lớp, không phản ánh riêng lớp dương. F1 mặc định của bài toán nhị phân đo lớp `target=1`, phù hợp với quality gate.

---

## 3. Khó Khăn Gặp Phải và Cách Giải Quyết

| Khó khăn | Nguyên nhân | Cách giải quyết |
|---|---|---|
| Serving không tải được model. | API mẫu dùng GCS, DVC remote dùng S3. | Chuyển API sang boto3, đồng bộ dependency. |
| Actions không truy cập được S3. | Runner không có credentials cục bộ. | Dùng secret `STORAGE_CREDENTIALS` trong job. |
| Model F1 thấp có thể được release. | Train thành công chưa đảm bảo ngưỡng 0.65. | Truyền F1 giữa các job, chặn release dưới ngưỡng. |

---

## 4. So Sánh Bước 2 và Bước 3 (bắt buộc, 2 - 3 câu)

| | f1_score | accuracy |
|---|---|---|
| Bước 2 (chỉ `train_batch1`) | 0.7149 | 0.874 |
| Bước 3 (thêm `train_batch2`) | 0.7354 | 0.882 |

**Nhận xét:** Bước 3 tăng F1 từ 0.7149 lên 0.7354 (+0.0205) và accuracy từ 0.874 lên 0.882 (+0.008). Trên tập đánh giá, kết quả tốt hơn sau khi bổ sung `train_batch2`.
