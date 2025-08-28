# 🛒 ECOMMERCE BACKEND PORTOFOLIO
Dokumentasi setup, penggunaan, dan pengembangan untuk project ini.
---
## ⚙️ Setup Project
1. **Buat virtual environment**
    ```bash
    python -m venv .venv 
    ```
2. **Aktifkan virtual environment**
    - Windows / bash:
        ```
        source .venv/Scripts/activate
        ```
    - Linux/MacOS:
        ```
        source .venv/bin/activate
        ```
3. **Upgrade pip**
    ```
    python.exe -m pip install --upgrade pip
    ```
4. **Install dependencies**
    ```
    pip install -r requirements.txt
    ```
5. **Jalankan migrasi database pertama kali**
    ```
    alembic upgrade head
    ```
## ▶️ Menjalankan Project
- **Setelah selesai setup:**
    ```
    uvicorn main:app --reload
    ```
    - Server akan jalan di: http://127.0.0.1:8000
    - Dokumentasi Swagger: http://127.0.0.1:8000/docs
- **Untuk menutup server, cukup tekan:**
    ```
    CTRL + C
    ```

## 🗄️ Menambah / Mengubah Tabel Database
Jika ada perubahan pada model:
1. **Buat file migrasi baru** 
    ```
    alembic revision --autogenerate -m "deskripsi perubahan"
    ```
2. **Jalankan migrasi**
    ```
    alembic upgrade head
    ```
3. **Jika butuh rollback**
    ```
    alembic downgrade -1
    ```