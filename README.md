# YouTube Data Pipeline

## 1. Tổng quan dự án

Project xây dựng một Data Pipeline tự động thu thập dữ liệu YouTube của 100 nghệ sĩ US-UK bằng YouTube Data API v3.

Pipeline sử dụng Python để Extract dữ liệu, lưu dữ liệu vào Google BigQuery RAW, sau đó thực hiện Transform bằng SQL và lưu kết quả vào BigQuery CLEAN.

Pipeline được triển khai trên Google Cloud VM và chạy tự động 2 lần mỗi ngày bằng cron.

## 2. Nguồn dữ liệu & lựa chọn nghệ sĩ

### Nguồn xếp hạng

Nguồn được sử dụng để xác định danh sách nghệ sĩ là **Chartmetric**.

Tiêu chí lựa chọn:

* 50 nghệ sĩ hàng đầu từ United States
* 50 nghệ sĩ hàng đầu từ United Kingdom
* Hai danh sách được gộp lại thành 100 nghệ sĩ.
* Danh sách sau đó được sắp xếp theo Chartmetric Rank để tạo danh sách Top 100 cuối cùng.

Ngày lấy dữ liệu: **19/09/2026**

YouTube Data API không được sử dụng để xác định thứ hạng nghệ sĩ. API chỉ được sử dụng để thu thập dữ liệu YouTube sau khi danh sách nghệ sĩ đã được xác định.

Danh sách nghệ sĩ và thông tin YouTube tương ứng được lưu tại:

```text
data/artists.csv
```

File bao gồm các thông tin chính:

```text
artist_name
channel_id
uploads_playlist_id
```

## 3. Kiến trúc

Pipeline có luồng xử lý:

```text
Chartmetric
    ↓
Top 100 Artists
    ↓
artists.csv
    ↓
YouTube Data API v3
    ↓
Extract
    ↓
Pandas DataFrame
    ↓
Load
    ↓
BigQuery RAW
    ↓
Transform bằng BigQuery SQL
    ↓
BigQuery CLEAN
```

Pipeline được điều khiển bởi `pipeline.py`.

Mỗi lần chạy pipeline sẽ tạo một `batch_id` dùng để xác định dữ liệu thuộc cùng một lần chạy.

Ví dụ:

```text
20261001_070000
```

## 4. Thu thập dữ liệu

Đối với mỗi nghệ sĩ:

1. Lấy danh sách video từ `uploads_playlist_id`.
2. Lấy thông tin chi tiết của các video.
3. Sắp xếp video theo `view_count`.
4. Chọn 10 video có lượt xem cao nhất.
5. Thu thập comment của 10 video này.

Quy tắc thu thập comment:

* Tối đa 2 trang comment cho mỗi video.
* Mỗi trang tối đa 100 comments.
* Chỉ lấy top-level comments.
* Không lấy chi tiết từng reply.
* Lưu `reply_count` của comment.

Pipeline có cơ chế retry đối với một số lỗi HTTP tạm thời và dừng khi YouTube API quota bị vượt quá.

## 5. BigQuery

Project sử dụng 2 dataset:

```text
youtube_raw
youtube_clean
```

### RAW

`youtube_raw` lưu dữ liệu sau khi Extract và flatten từ YouTube API.

Mỗi lần chạy tạo một bộ bảng mới theo `batch_id`.

Ví dụ:

```text
youtube_raw.videos_20261001_070000
youtube_raw.comments_20261001_070000
```

RAW được giữ lại để có thể đối soát và thực hiện transformation lại khi cần.

### CLEAN

`youtube_clean` chứa dữ liệu sau khi được làm sạch và transform bằng BigQuery SQL.

Ví dụ:

```text
youtube_clean.videos_20261001_070000
youtube_clean.comments_20261001_070000
```

Một số bước xử lý gồm:

* Loại bỏ bản ghi thiếu ID.
* `TRIM()` các trường text.
* Thay thế một số giá trị NULL của các trường số bằng `0`.
* Giữ lại metadata của pipeline.

## 6. Cấu trúc project

```text
big_proj_1/
│
├── elt/
│   ├── __init__.py
│   ├── config.py
│   ├── extract.py
│   ├── load.py
│   ├── transform.py
│   └── pipeline.py
│
├── data/
│   └── artists.csv
│
├── requirements.txt
├── run.sh
├── .env
├── .gitignore
└── README.md
```

Vai trò của các file chính:

```text
config.py      → Quản lý cấu hình
extract.py     → Thu thập dữ liệu từ YouTube API
load.py        → Load DataFrame vào BigQuery RAW
transform.py   → Transform RAW thành CLEAN bằng SQL
pipeline.py    → Điều phối toàn bộ pipeline
artists.csv    → Danh sách 100 nghệ sĩ và YouTube channel
run.sh         → Chạy pipeline
```

## 7. Cài đặt & chạy

### Clone project

```bash
git clone <repository-url>
cd big_proj_1
```

### Tạo virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Cài đặt thư viện

```bash
pip install -r requirements.txt
```

### Cấu hình

Tạo file `.env`:

```env
GCP_PROJECT_ID=your-project-id
YOUTUBE_API_KEY=your-youtube-api-key
```

Khi chạy local, có thể sử dụng Google Application Credentials để xác thực với Google Cloud.

Không đưa API key hoặc thông tin xác thực thật vào GitHub.

### Chạy pipeline

```bash
./run.sh
```

Hoặc:

```bash
python -m elt.pipeline
```

## 8. Scheduling & Security

### Scheduling

Pipeline được triển khai trên Google Cloud VM và chạy tự động 2 lần mỗi ngày bằng cron:

```text
07:00
23:00
```

Cron sử dụng `run.sh` để khởi chạy pipeline.

Ví dụ:

```cron
0 7 * * * /home/user/big_proj_1/run.sh
0 23 * * * /home/user/big_proj_1/run.sh
```

### Security

Các thông tin nhạy cảm không được lưu trực tiếp trong source code.

* YouTube API key được lưu trong biến môi trường.
* File `.env` không được commit lên GitHub.
* Service Account credentials không được commit lên GitHub.
* Google Cloud VM sử dụng Service Account để truy cập các tài nguyên cần thiết trên Google Cloud.