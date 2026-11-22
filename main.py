from __future__ import annotations

import sqlite3
import tkinter as tk
from contextlib import contextmanager
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Dict, Iterator, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# KONFIGURASI
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).resolve().parent / "mahasiswa.db"
DAFTAR_PRODI = [
    "Informatika",
    "Sistem Informasi",
    "Manajemen",
    "Akuntansi",
]


# ---------------------------------------------------------------------------
# LAPISAN DATABASE
# ---------------------------------------------------------------------------

class DatabaseMahasiswa:
    """Mengelola koneksi, skema, migrasi, dan operasi database mahasiswa."""

    def __init__(self, db_path: Union[Path, str] = DB_PATH) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def koneksi(self) -> Iterator[sqlite3.Connection]:
        """Membuka koneksi; commit jika berhasil, rollback jika gagal, lalu tutup."""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def inisialisasi(self) -> None:
        """Membuat tabel dan memigrasikan kolom yang belum ada pada database lama."""
        with self.koneksi() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mahasiswa (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nama TEXT NOT NULL,
                    nim TEXT NOT NULL,
                    prodi TEXT NOT NULL,
                    alamat TEXT,
                    angkatan INTEGER
                )
                """
            )

            info_kolom = conn.execute(
                "PRAGMA table_info(mahasiswa)"
            ).fetchall()
            kolom_tersedia = {str(row["name"]).lower() for row in info_kolom}

            # Kolom inti harus ada. Skema lama dari modul sudah memiliki kolom ini.
            kolom_wajib = {"id", "nama", "nim", "prodi"}
            kolom_hilang = kolom_wajib - kolom_tersedia
            if kolom_hilang:
                nama_kolom = ", ".join(sorted(kolom_hilang))
                raise RuntimeError(
                    "Struktur tabel 'mahasiswa' tidak sesuai. "
                    f"Kolom inti yang tidak ditemukan: {nama_kolom}. "
                    "Cadangkan database, lalu periksa skema tabel."
                )

            # Migrasi aman untuk database lama yang belum memiliki kolom ini.
            if "alamat" not in kolom_tersedia:
                conn.execute("ALTER TABLE mahasiswa ADD COLUMN alamat TEXT")
            if "angkatan" not in kolom_tersedia:
                conn.execute("ALTER TABLE mahasiswa ADD COLUMN angkatan INTEGER")

            # Menjamin NIM unik juga pada database lama yang mungkin belum
            # memiliki constraint UNIQUE. Jika terdapat NIM ganda, SQLite
            # menolak pembuatan index dan pengguna diberi pesan kesalahan.
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_mahasiswa_nim_unique
                ON mahasiswa(nim)
                """
            )

    def ambil_semua(self, kata_kunci: str = "") -> List[Dict[str, object]]:
        """Mengambil semua data atau mencari berdasarkan nama/NIM."""
        with self.koneksi() as conn:
            if kata_kunci:
                pola = f"%{kata_kunci}%"
                rows = conn.execute(
                    """
                    SELECT id, nama, nim, prodi, alamat, angkatan
                    FROM mahasiswa
                    WHERE nama LIKE ? OR nim LIKE ?
                    ORDER BY id DESC
                    """,
                    (pola, pola),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, nama, nim, prodi, alamat, angkatan
                    FROM mahasiswa
                    ORDER BY id DESC
                    """
                ).fetchall()

        return [dict(row) for row in rows]

    def ambil_berdasarkan_id(self, record_id: int) -> Optional[Dict[str, object]]:
        """Mengambil satu record berdasarkan primary key."""
        with self.koneksi() as conn:
            row = conn.execute(
                """
                SELECT id, nama, nim, prodi, alamat, angkatan
                FROM mahasiswa
                WHERE id = ?
                """,
                (record_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def tambah(
        self,
        nama: str,
        nim: str,
        prodi: str,
        alamat: str,
        angkatan: int,
    ) -> None:
        with self.koneksi() as conn:
            conn.execute(
                """
                INSERT INTO mahasiswa (nama, nim, prodi, alamat, angkatan)
                VALUES (?, ?, ?, ?, ?)
                """,
                (nama, nim, prodi, alamat, angkatan),
            )

    def ubah(
        self,
        record_id: int,
        nama: str,
        nim: str,
        prodi: str,
        alamat: str,
        angkatan: int,
    ) -> bool:
        with self.koneksi() as conn:
            cursor = conn.execute(
                """
                UPDATE mahasiswa
                SET nama = ?, nim = ?, prodi = ?, alamat = ?, angkatan = ?
                WHERE id = ?
                """,
                (nama, nim, prodi, alamat, angkatan, record_id),
            )
            return cursor.rowcount > 0

    def hapus(self, record_id: int) -> bool:
        with self.koneksi() as conn:
            cursor = conn.execute(
                "DELETE FROM mahasiswa WHERE id = ?",
                (record_id,),
            )
            return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# ANTARMUKA TKINTER
# ---------------------------------------------------------------------------

class AplikasiMahasiswa:
    """Antarmuka desktop untuk mengelola data mahasiswa."""

    def __init__(self, root: tk.Tk, database: DatabaseMahasiswa) -> None:
        self.root = root
        self.database = database
        self.record_terpilih: Optional[int] = None
        self.kata_kunci_aktif = ""

        self.root.title("Aplikasi Data Mahasiswa")
        self.root.geometry("1120x720")
        self.root.minsize(900, 620)

        self._atur_style()
        self._buat_widget()
        self.tampilkan_data()

    def _atur_style(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Treeview", rowheight=27)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("Judul.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Bantuan.TLabel", foreground="#555555")

    def _buat_widget(self) -> None:
        wadah = ttk.Frame(self.root, padding=14)
        wadah.pack(fill="both", expand=True)
        wadah.columnconfigure(0, weight=1)

        ttk.Label(
            wadah,
            text="APLIKASI DATA MAHASISWA",
            style="Judul.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 3))

        ttk.Label(
            wadah,
            text="Pengelolaan data menggunakan Python, Tkinter, dan SQLite",
            style="Bantuan.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        # Formulir
        form = ttk.LabelFrame(wadah, text="Formulir Mahasiswa", padding=12)
        form.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        for kolom in (1, 3):
            form.columnconfigure(kolom, weight=1)

        ttk.Label(form, text="Nama *").grid(
            row=0, column=0, padx=5, pady=6, sticky="w"
        )
        self.entry_nama = ttk.Entry(form)
        self.entry_nama.grid(
            row=0, column=1, padx=5, pady=6, sticky="ew"
        )

        ttk.Label(form, text="NIM *").grid(
            row=0, column=2, padx=5, pady=6, sticky="w"
        )
        self.entry_nim = ttk.Entry(form)
        self.entry_nim.grid(
            row=0, column=3, padx=5, pady=6, sticky="ew"
        )

        ttk.Label(form, text="Program Studi *").grid(
            row=1, column=0, padx=5, pady=6, sticky="w"
        )
        self.combo_prodi = ttk.Combobox(
            form,
            values=DAFTAR_PRODI,
            state="readonly",
        )
        self.combo_prodi.grid(
            row=1, column=1, padx=5, pady=6, sticky="ew"
        )

        ttk.Label(form, text="Alamat").grid(
            row=1, column=2, padx=5, pady=6, sticky="w"
        )
        self.entry_alamat = ttk.Entry(form)
        self.entry_alamat.grid(
            row=1, column=3, padx=5, pady=6, sticky="ew"
        )

        ttk.Label(form, text="Angkatan *").grid(
            row=2, column=0, padx=5, pady=6, sticky="w"
        )
        self.entry_angkatan = ttk.Entry(form)
        self.entry_angkatan.grid(
            row=2, column=1, padx=5, pady=6, sticky="ew"
        )

        ttk.Label(
            form,
            text="* Wajib diisi. Angkatan harus berupa bilangan bulat.",
            style="Bantuan.TLabel",
        ).grid(row=2, column=2, columnspan=2, padx=5, pady=6, sticky="w")

        # Baris tombol aksi
        aksi = ttk.Frame(wadah)
        aksi.grid(row=3, column=0, sticky="new", pady=(0, 8))

        self.btn_simpan = ttk.Button(
            aksi, text="Simpan Data", command=self.simpan_data
        )
        self.btn_simpan.pack(side="left", padx=(0, 5))

        self.btn_ubah = ttk.Button(
            aksi,
            text="Ubah Data Terpilih",
            command=self.ubah_data,
            state="disabled",
        )
        self.btn_ubah.pack(side="left", padx=5)

        ttk.Button(
            aksi, text="Bersihkan Form", command=self.bersihkan_form
        ).pack(side="left", padx=5)

        ttk.Button(
            aksi, text="Refresh", command=self.refresh_data
        ).pack(side="left", padx=5)

        self.btn_hapus = ttk.Button(
            aksi,
            text="Hapus Data Terpilih",
            command=self.hapus_data,
        )
        self.btn_hapus.pack(side="right", padx=(5, 0))

        # Pencarian
        pencarian = ttk.LabelFrame(wadah, text="Pencarian", padding=9)
        pencarian.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        pencarian.columnconfigure(1, weight=1)

        ttk.Label(pencarian, text="Nama atau NIM:").grid(
            row=0, column=0, padx=(3, 7), sticky="w"
        )
        self.entry_cari = ttk.Entry(pencarian)
        self.entry_cari.grid(row=0, column=1, padx=4, sticky="ew")
        self.entry_cari.bind("<Return>", self.cari_data)

        ttk.Button(
            pencarian, text="Cari", command=self.cari_data
        ).grid(row=0, column=2, padx=4)

        ttk.Button(
            pencarian,
            text="Tampilkan Semua",
            command=self.tampilkan_semua,
        ).grid(row=0, column=3, padx=4)

        # Tabel data dan scrollbar
        area_tabel = ttk.Frame(wadah)
        area_tabel.grid(row=5, column=0, sticky="nsew")
        wadah.rowconfigure(5, weight=1)
        area_tabel.rowconfigure(0, weight=1)
        area_tabel.columnconfigure(0, weight=1)

        kolom = ("id", "nama", "nim", "prodi", "alamat", "angkatan")
        self.tabel = ttk.Treeview(
            area_tabel,
            columns=kolom,
            show="headings",
            selectmode="browse",
        )

        konfigurasi_kolom = [
            ("id", "ID", 55, "center"),
            ("nama", "Nama", 190, "w"),
            ("nim", "NIM", 125, "center"),
            ("prodi", "Program Studi", 165, "w"),
            ("alamat", "Alamat", 280, "w"),
            ("angkatan", "Angkatan", 95, "center"),
        ]
        for key, judul, lebar, anchor in konfigurasi_kolom:
            self.tabel.heading(key, text=judul)
            self.tabel.column(key, width=lebar, minwidth=55, anchor=anchor)

        scrollbar_y = ttk.Scrollbar(
            area_tabel, orient="vertical", command=self.tabel.yview
        )
        scrollbar_x = ttk.Scrollbar(
            area_tabel, orient="horizontal", command=self.tabel.xview
        )
        self.tabel.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
        )

        self.tabel.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        self.tabel.bind("<<TreeviewSelect>>", self.isi_form_dari_tabel)

        # Status jumlah record
        self.label_status = ttk.Label(
            wadah, text="Jumlah mahasiswa: 0", style="Bantuan.TLabel"
        )
        self.label_status.grid(row=6, column=0, sticky="w", pady=(7, 0))

    # ------------------------------------------------------------------
    # UTILITAS FORMULIR DAN VALIDASI
    # ------------------------------------------------------------------

    def _ambil_nilai_form(self) -> Optional[Tuple[str, str, str, str, int]]:
        nama = self.entry_nama.get().strip()
        nim = self.entry_nim.get().strip()
        prodi = self.combo_prodi.get().strip()
        alamat = self.entry_alamat.get().strip()
        angkatan_text = self.entry_angkatan.get().strip()

        if not nama or not nim or not prodi or not angkatan_text:
            messagebox.showwarning(
                "Validasi",
                "Nama, NIM, Program Studi, dan Angkatan wajib diisi.",
                parent=self.root,
            )
            return None

        # isdigit() mempertahankan ketentuan pengembangan pada modul.
        if not angkatan_text.isdigit():
            messagebox.showwarning(
                "Validasi",
                "Angkatan harus berupa bilangan bulat, misalnya 2024.",
                parent=self.root,
            )
            self.entry_angkatan.focus_set()
            return None

        try:
            angkatan = int(angkatan_text)
        except ValueError:
            messagebox.showwarning(
                "Validasi", "Nilai angkatan tidak valid.", parent=self.root
            )
            self.entry_angkatan.focus_set()
            return None

        return nama, nim, prodi, alamat, angkatan

    def _kosongkan_widget_form(self) -> None:
        self.entry_nama.delete(0, tk.END)
        self.entry_nim.delete(0, tk.END)
        self.combo_prodi.set("")
        self.entry_alamat.delete(0, tk.END)
        self.entry_angkatan.delete(0, tk.END)

    def bersihkan_form(self) -> None:
        self._kosongkan_widget_form()
        self.record_terpilih = None
        pilihan = self.tabel.selection()
        if pilihan:
            self.tabel.selection_remove(*pilihan)
        self.btn_ubah.configure(state="disabled")
        self.entry_nama.focus_set()

    # ------------------------------------------------------------------
    # TAMPILAN DATA DAN PENCARIAN
    # ------------------------------------------------------------------

    def _isi_tabel(self, daftar_data: List[Dict[str, object]]) -> None:
        for item in self.tabel.get_children():
            self.tabel.delete(item)

        for data in daftar_data:
            nilai = (
                data["id"],
                data["nama"] or "",
                data["nim"] or "",
                data["prodi"] or "",
                data["alamat"] or "",
                data["angkatan"] if data["angkatan"] is not None else "",
            )
            self.tabel.insert("", tk.END, values=nilai)

        self.label_status.configure(
            text=f"Jumlah mahasiswa ditampilkan: {len(daftar_data)}"
        )

    def tampilkan_data(self) -> None:
        """Memuat data sesuai kata kunci pencarian yang sedang aktif."""
        try:
            daftar_data = self.database.ambil_semua(self.kata_kunci_aktif)
            self._isi_tabel(daftar_data)
        except (sqlite3.Error, OSError) as error:
            messagebox.showerror(
                "Kesalahan Database",
                f"Data tidak dapat ditampilkan.\n\nDetail: {error}",
                parent=self.root,
            )

    def refresh_data(self) -> None:
        # Refresh memuat ulang daftar dan membatalkan pilihan lama agar
        # tombol Ubah/Hapus tidak memakai ID yang sudah tidak terpilih.
        self.record_terpilih = None
        self._kosongkan_widget_form()
        self.btn_ubah.configure(state="disabled")
        self.tampilkan_data()

    def cari_data(self, event: Optional[tk.Event] = None) -> None:
        self.kata_kunci_aktif = self.entry_cari.get().strip()
        self.tampilkan_data()
        self.record_terpilih = None
        self._kosongkan_widget_form()
        self.btn_ubah.configure(state="disabled")

    def tampilkan_semua(self) -> None:
        self.entry_cari.delete(0, tk.END)
        self.kata_kunci_aktif = ""
        self.record_terpilih = None
        self._kosongkan_widget_form()
        self.btn_ubah.configure(state="disabled")
        self.tampilkan_data()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def simpan_data(self) -> None:
        nilai = self._ambil_nilai_form()
        if nilai is None:
            return

        nama, nim, prodi, alamat, angkatan = nilai
        try:
            self.database.tambah(nama, nim, prodi, alamat, angkatan)
            messagebox.showinfo(
                "Berhasil", "Data mahasiswa berhasil disimpan.", parent=self.root
            )
            self.bersihkan_form()
            self.tampilkan_data()
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "NIM Duplikat",
                "NIM sudah terdaftar. Gunakan NIM yang berbeda.",
                parent=self.root,
            )
        except (sqlite3.Error, OSError) as error:
            messagebox.showerror(
                "Kesalahan Database",
                f"Data gagal disimpan.\n\nDetail: {error}",
                parent=self.root,
            )

    def isi_form_dari_tabel(self, event: Optional[tk.Event] = None) -> None:
        pilihan = self.tabel.selection()
        if not pilihan:
            return

        try:
            nilai = self.tabel.item(pilihan[0], "values")
            if not nilai:
                return
            record_id = int(nilai[0])
            data = self.database.ambil_berdasarkan_id(record_id)
            if data is None:
                messagebox.showwarning(
                    "Data Tidak Ditemukan",
                    "Record tidak lagi tersedia di database. Tekan Refresh.",
                    parent=self.root,
                )
                self.tampilkan_data()
                self.bersihkan_form()
                return

            # Ambil ulang dari SQLite agar NIM seperti '00123' tidak
            # berubah akibat interpretasi nilai dari Treeview.
            self._kosongkan_widget_form()
            self.entry_nama.insert(0, str(data["nama"] or ""))
            self.entry_nim.insert(0, str(data["nim"] or ""))
            self.combo_prodi.set(str(data["prodi"] or ""))
            self.entry_alamat.insert(0, str(data["alamat"] or ""))
            if data["angkatan"] is not None:
                self.entry_angkatan.insert(0, str(data["angkatan"]))

            self.record_terpilih = record_id
            self.btn_ubah.configure(state="normal")
        except (sqlite3.Error, OSError, ValueError, TypeError) as error:
            messagebox.showerror(
                "Kesalahan",
                f"Data terpilih tidak dapat dimuat.\n\nDetail: {error}",
                parent=self.root,
            )

    def ubah_data(self) -> None:
        if self.record_terpilih is None:
            messagebox.showwarning(
                "Pilih Data", "Pilih baris mahasiswa yang akan diubah.", parent=self.root
            )
            return

        nilai = self._ambil_nilai_form()
        if nilai is None:
            return

        nama, nim, prodi, alamat, angkatan = nilai
        try:
            berhasil = self.database.ubah(
                self.record_terpilih, nama, nim, prodi, alamat, angkatan
            )
            if not berhasil:
                messagebox.showwarning(
                    "Data Tidak Ditemukan",
                    "Data yang akan diubah sudah tidak tersedia. Muat ulang tabel.",
                    parent=self.root,
                )
                self.bersihkan_form()
                self.tampilkan_data()
                return

            messagebox.showinfo(
                "Berhasil", "Data mahasiswa berhasil diperbarui.", parent=self.root
            )
            self.bersihkan_form()
            self.tampilkan_data()
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "NIM Duplikat",
                "NIM tersebut sudah digunakan oleh mahasiswa lain.",
                parent=self.root,
            )
        except (sqlite3.Error, OSError) as error:
            messagebox.showerror(
                "Kesalahan Database",
                f"Data gagal diperbarui.\n\nDetail: {error}",
                parent=self.root,
            )

    def hapus_data(self) -> None:
        if self.record_terpilih is None:
            messagebox.showwarning(
                "Pilih Data", "Pilih baris mahasiswa yang akan dihapus.", parent=self.root
            )
            return

        nama = self.entry_nama.get().strip() or "mahasiswa ini"
        konfirmasi = messagebox.askyesno(
            "Konfirmasi Hapus",
            f"Apakah Anda yakin ingin menghapus data {nama}?\n"
            "Data yang dihapus tidak dapat dikembalikan.",
            parent=self.root,
        )
        if not konfirmasi:
            return

        try:
            berhasil = self.database.hapus(self.record_terpilih)
            if not berhasil:
                messagebox.showwarning(
                    "Data Tidak Ditemukan",
                    "Data sudah tidak tersedia di database.",
                    parent=self.root,
                )
            else:
                messagebox.showinfo(
                    "Berhasil", "Data mahasiswa berhasil dihapus.", parent=self.root
                )

            self.bersihkan_form()
            self.tampilkan_data()
        except (sqlite3.Error, OSError) as error:
            messagebox.showerror(
                "Kesalahan Database",
                f"Data gagal dihapus.\n\nDetail: {error}",
                parent=self.root,
            )


# ---------------------------------------------------------------------------
# TITIK MASUK PROGRAM
# ---------------------------------------------------------------------------

def main() -> None:
    root = tk.Tk()
    root.withdraw()

    try:
        database = DatabaseMahasiswa(DB_PATH)
        database.inisialisasi()
        AplikasiMahasiswa(root, database)
    except (sqlite3.Error, OSError, RuntimeError) as error:
        messagebox.showerror(
            "Gagal Membuka Aplikasi",
            "Aplikasi tidak dapat menyiapkan database.\n\n"
            f"Detail: {error}\n\n"
            "Jika file database sedang dibuka di DB Browser, tutup atau "
            "selesaikan perubahan di DB Browser lalu jalankan kembali aplikasi.",
            parent=root,
        )
        root.destroy()
        return

    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    main()
