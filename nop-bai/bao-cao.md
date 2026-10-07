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

**Lý do:** Run 3 đạt F1 cao nhất (0.7149), vượt 0.65; Run 1: 0.7109, Run 2: 0.6051. Run 1 có accuracy cao hơn (0.878 so với 0.874) nhưng F1 thấp hơn. Run 3 giữ learning rate 0.1, tăng số cây/độ sâu, F1 tăng thêm 0.004; Run 2 đổi ba tham số nên khó tách ảnh hưởng.

---

## 2. Vì Sao Ngưỡng Chất Lượng Đặt Trên F1 Chứ Không Phải Accuracy

Adult có 45.222 mẫu sau khi bỏ dòng thiếu; lớp thu nhập trên 50K chiếm 24,8%, lớp thấp chiếm 75,2%. Vì lệch lớp, mô hình luôn đoán “thu nhập thấp” vẫn đạt accuracy 0,752 nhưng bỏ sót toàn bộ lớp dương, nên con số này gây hiểu nhầm. F1 lớp dương là trung bình điều hòa của precision (tỷ lệ dự đoán thu nhập cao đúng) và recall (tỷ lệ người thu nhập cao được tìm thấy); nó phản ánh cả dự đoán nhầm lẫn bỏ sót, điều accuracy không thể hiện. Không dùng `average="weighted"` vì lớp đa số có thể chi phối điểm; không dùng `average="macro"` vì nó trung bình F1 của hai lớp thay vì tập trung vào lớp dương. `f1_score` nhị phân mặc định tính riêng nhãn 1, khớp mục tiêu và quality gate.

---

## 3. Khó Khăn Gặp Phải và Cách Giải Quyết

| Khó khăn | Nguyên nhân | Cách giải quyết |
|---|---|---|
| Serving không tải model. | API dùng GCS, DVC dùng S3. | Chuyển sang boto3. |
| Actions lỗi S3. | Runner thiếu credentials. | Dùng secret `STORAGE_CREDENTIALS`. |
| Model F1 thấp vẫn release. | Thiếu gate. | Chặn dưới 0.65. |

---

## 4. So Sánh Bước 2 và Bước 3 (bắt buộc, 2 - 3 câu)

| | f1_score | accuracy |
|---|---|---|
| Bước 2 (chỉ `train_batch1`) | 0.7149 | 0.874 |
| Bước 3 (thêm `train_batch2`) | 0.7354 | 0.882 |

**Nhận xét:** Bước 3 tăng F1 (+0.0205) và accuracy (+0.008). Kết quả trên tập đánh giá tốt hơn sau khi thêm `train_batch2`.

---

## 5. Phần Bonus Đã Thực Hiện

- [x] Bonus 1 - DagsHub: cấu hình tracking URI và xác thực bằng GitHub Secrets.
- [x] Bonus 2 - Quét ngưỡng 0,10–0,90, chọn F1 tối ưu và lưu vào model.
- [x] Bonus 3 - Tạo artifact confusion matrix, precision/recall theo lớp.
- [x] Bonus 4 - Chặn release nếu F1 mới thấp hơn bản trên S3.
- [x] Bonus 5 - Cảnh báo drift nếu tỷ lệ lớp dương lệch >5 điểm % so với 24,8%.
