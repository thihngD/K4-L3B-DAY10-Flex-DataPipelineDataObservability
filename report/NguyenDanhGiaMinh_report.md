# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Nguyễn Danh Gia Minh |
| MSSV | 2A202602441 |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | Flex |
| Vai trò chính | M1 — Source & Corruption owner |
| Repository | https://github.com/thihngD/K4-L3B-DAY10-Flex-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 (phần M1; official run chưa hoàn tất) |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| Crossref ingestion | `src/ingestion/crossref.py`: `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` | `Settings`, Crossref payload hoặc snapshot local | `list[PaperRecord]`, `data/raw/crossref_records.json`; raw response được giữ tại `data/raw/crossref_response.json` | Hoàn thành, nghiệm thu snapshot 24 records và retry/fallback bằng mock |
| Corruption | `src/ingestion/corruption.py`: `corrupt_clean_dataframe` | DataFrame từ `build_clean_dataframe` theo C2 và đường dẫn log | DataFrame corrupted đúng schema cùng log JSON theo C5 | Đã kiểm thử với clean thật: 24→21 dòng; official artifact do M4 tạo khi chạy flow |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Chưa ghi nhận hoạt động hỗ trợ ngoài phạm vi M1 trong phần việc này. | — | — |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Parse, fetch và load raw records theo C1 | `src/ingestion/crossref.py`; `data/raw/crossref_records.json` | Snapshot mode trả 24 records; raw records được ghi lại và giữ nguyên so với artifact hiện có | Lệnh C1 tại §4; `git diff --stat -- data/raw` không có thay đổi |
| Retry và fallback khi lỗi mạng | `fetch_source_records` | Mock timeout xác nhận tối đa 4 request (request đầu + 3 retry), backoff 1/2/4 giây, fallback snapshot trả 24 records | Python mock với `requests.get` và `time.sleep` |
| Tạo corruption tất định theo C5 | `src/ingestion/corruption.py`; `src/ingestion/cleaning.py` | Clean thật 24 dòng → corrupted 21 dòng; counts `[5, 3, 3, 3, 6, 2]`; đúng 16 cột, không null, input không bị mutate; `text_for_embedding` khớp helper C2 | Inline Python assertions qua `build_clean_dataframe` và `corrupt_clean_dataframe`; log ghi vào thư mục tạm |

Output cụ thể: `data/raw/crossref_records.json` chứa 24 records. Tích hợp C2→C5 đã chạy trên clean thật và cho 24→21 dòng; log kiểm thử được ghi trong thư mục tạm, chưa có `data/results/corruption_log.json` từ official pipeline run. Hai file code M1 đã được push lên branch `gminh`, commit `d9002a4`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

M1 cung cấp raw records tái lập được cho M2/M4 và tạo corruption có kiểm soát để M3/M4 đo các tín hiệu quality/freshness cùng ảnh hưởng lên retrieval. Raw snapshot cũng là nguồn tin cậy để M4 dựng lại dữ liệu khi repair.

### Cách triển khai

`parse_crossref_payload` chuẩn hóa title/abstract bằng cách bỏ tag, giải mã HTML và chuẩn hóa khoảng trắng; ánh xạ authors/categories, ngày và URL; bỏ record thiếu DOI, title, abstract hoặc ngày hợp lệ. `fetch_source_records` dùng snapshot khi `refresh_source=False`; khi refresh, gọi Crossref với timeout, retry/backoff và fallback snapshot nếu request thất bại. Raw records được serialize bằng `dataclasses.asdict`.

`corrupt_clean_dataframe` copy đầu vào, dùng `numpy.random.default_rng(42)` để chọn các dòng không chồng lấn, áp dụng đúng sáu scenario C5 theo thứ tự, tính lại `summary_chars` và `text_for_embedding`, rồi sort theo C2 và ghi corruption log. Hiện module import và dùng `compose_text_for_embedding` do M2 cung cấp; fallback giữ cùng định dạng 5 phần cho trường hợp chạy song song trước khi helper có mặt.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | C1: Settings và Crossref payload/snapshot. C5: DataFrame 16 cột theo C2 và đường dẫn log. |
| Output | C1: `list[PaperRecord]` 11 trường và raw records JSON. C5: DataFrame corrupted theo C2 và corruption log JSON. |
| Module phụ thuộc | `core.config`, `core.utils`, `requests`, `pandas`, `numpy`; hàm compose text C2 của M2 khi đã có. |
| Module sử dụng output | `ingestion.cleaning`/M2, `pipelines.phase1` và `pipelines.corruption_flow`/M4; M3 dùng corruption log để lập báo cáo. |
| Điều kiện lỗi cần xử lý | Record thiếu trường bắt buộc/ngày hợp lệ bị bỏ; lỗi mạng được retry rồi fallback snapshot; corruption không mutate input, không sinh null và vẫn chạy với fixture nhỏ. |

### Cách xác minh

```powershell
$env:PYTHONPATH='src'
py -3.11 -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
```

- **Kết quả mong đợi:** Snapshot được dùng mặc định, trả 24 records.
- **Kết quả thực tế:** `[crossref] mode=snapshot records=24`; `Đã tải 24 bài báo`. Mock timeout xác nhận retry/backoff/fallback. Fixture C5 cho 12→9. Tích hợp `build_clean_dataframe`→`corrupt_clean_dataframe` cho clean thật 24→21 với counts `[5, 3, 3, 3, 6, 2]`; đúng schema, không null, input không đổi và text dùng helper C2.
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`; log C5 trong các test được ghi tạm, không phải official artifact.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần dùng nguồn dữ liệu nhất quán giữa các lần chạy, kể cả khi Crossref không truy cập được.
- **Các phương án đã cân nhắc:** Gọi API mỗi lần chạy; hoặc dùng snapshot mặc định và chỉ refresh khi cấu hình yêu cầu.
- **Phương án đã chọn:** Snapshot-first khi `refresh_source=False`; khi refresh thì retry lỗi phù hợp và fallback snapshot.
- **Lý do:** Snapshot giúp tái lập kết quả và không phụ thuộc mạng trong lần chạy mặc định; refresh vẫn có thể chủ động lấy dữ liệu mới.
- **Bằng chứng quyết định phù hợp:** Snapshot trả 24 records; test mock timeout cho thấy retry/backoff và fallback hoạt động. Raw artifacts không thay đổi sau kiểm tra.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'core'` khi chạy bằng lệnh `python` mặc định.
- **Lệnh hoặc bước tái hiện:** Chạy nghiệm thu C1 bằng `python -c ...` trong môi trường mặc định.
- **Nguyên nhân gốc:** `python` trỏ Python 3.10 và package source chưa ở import path; project yêu cầu Python 3.11 trở lên. Python 3.11 ban đầu cũng thiếu dependency tối thiểu.
- **Cách xử lý:** Dùng Python 3.11, đặt `PYTHONPATH=src` và cài các dependency tối thiểu cho kiểm thử M1.
- **Cách xác minh sau khi sửa:** Chạy lệnh C1 ở §4, nhận được 24 records từ snapshot.
- **Điều học được:** Kiểm tra interpreter, import path và dependency trước khi quy lỗi import cho logic ứng dụng.

Blocker tích hợp còn mở:

- **Phạm vi bị ảnh hưởng:** `script/check_contracts.py` được rules tham chiếu nhưng hiện không có trong repo; chưa có official corruption log/metrics từ flow M4.
- **Những gì đã loại trừ:** Đã chạy clean thật từ `build_clean_dataframe` qua C5; kiểm tra đúng 16 cột, không null, không mutate baseline, counts đúng và embedding text khớp helper M2.
- **Bước tiếp theo:** M4 chạy official `corruption_flow`; đối chiếu artifact log/quality/metrics thực tế. Chạy checker contract nếu nhóm bổ sung script.

## 7. Hiểu biết về luồng end-to-end

1. M1 lấy Crossref payload hoặc snapshot và lưu raw records; M2 làm sạch thành schema C2, tính `age_days` và `text_for_embedding`; M4 tạo embeddings và ChromaDB index từ dữ liệu sạch.
2. Test set chứa câu hỏi, ground-truth answer và `ground_truth_doc_ids`. Evaluation so sánh IDs được truy hồi với ID mong đợi để tính retrieval hit rate, đồng thời so câu trả lời với ground truth để tính answer metrics.
3. Quality checks kiểm tra schema/chất lượng như completeness, uniqueness và độ dài. Freshness dùng `age_days` để tính tỷ lệ records vượt ngưỡng và so với SLA. Giá trị chuỗi rỗng có thể qua kiểm tra not-null nhưng vẫn fail kiểm tra độ dài.
4. Giữ cùng test set cho baseline, corrupted và repaired để câu hỏi/ground truth không đổi; nhờ vậy khác biệt metrics phản ánh thay đổi dữ liệu thay vì benchmark.
5. Repair cần dựng lại clean từ raw records, xác minh tập `paper_id` và số dòng khớp baseline, rồi so quality/freshness cùng metrics repaired với baseline. Chưa có official run để kết luận mức phục hồi thực tế.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
|---|---:|---:|---:|---|
| `retrieval_hit_rate` | N/A | N/A | N/A | Chưa có official run |
| `mean_token_f1` | N/A | N/A | N/A | Chưa có official run |
| `judge_accuracy` | N/A | N/A | N/A | Chưa có official run |
| `mean_judge_score` | N/A | N/A | N/A | Chưa có official run |
| Quality checks | N/A | N/A | N/A | Chưa có official run |
| Freshness status | N/A | N/A | N/A | Chưa có official run |

### Kết luận từ số liệu

1. Chưa kết luận: cần corruption log, corrupted quality/freshness report và metrics từ official run để xác lập chuỗi bằng chứng.
2. Chưa kết luận: cần repaired quality/freshness report và repaired metrics từ official run để xác định mức phục hồi.

**Corruption ảnh hưởng rõ nhất:** Chưa xác định; không suy diễn từ fixture hoặc DataFrame kiểm thử. Sẽ đối chiếu `corrupted_answers.json`, quality report và metrics official.

**Kết quả khác kỳ vọng:** Chưa có official result để so sánh với kỳ vọng C4; cập nhật sau khi M4 chạy flow tích hợp.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Snapshot raw bất biến giúp các module dùng cùng nguồn dữ liệu và cho phép tái dựng pipeline.
2. Freshness là tín hiệu riêng với kiểm tra schema/null; dữ liệu rỗng hoặc cũ cần check tương ứng để tránh silent failure.
3. Corruption cần tất định và log rõ records bị tác động để liên hệ thay đổi dữ liệu với quality và RAG metrics.

### Nếu có thêm thời gian

Bổ sung pytest cho parser (ngày thiếu tháng/ngày, JATS/HTML, record thiếu trường bắt buộc), retry/fallback và corruption determinism; đo bằng coverage và chạy lặp để đảm bảo output/log ổn định.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [ ] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Danh Gia Minh  
**Ngày xác nhận:** [Bạn tự xác nhận sau khi rà soát]
