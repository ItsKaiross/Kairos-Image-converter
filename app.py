import os
import threading
import struct
import io
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

FORMATS  = ["JPEG", "PNG", "WEBP", "BMP", "TIFF", "GIF", "HEIC", "ICO"]
ICO_SIZES = [256, 128, 64, 48, 32, 16]

# ── palette ────────────────────────────────────────────────────────────────────
BG       = "#0f0f17"
SURFACE  = "#1a1a2e"
CARD     = "#16213e"
BORDER   = "#2a2a4a"
ACCENT   = "#7c3aed"
ACCENT2  = "#a855f7"
SUCCESS  = "#22c55e"
ERROR    = "#ef4444"
TEXT     = "#e2e8f0"
SUBTEXT  = "#94a3b8"

# ── ICO helpers ────────────────────────────────────────────────────────────────
def _crop_transparent_padding(img):
    bbox = img.getchannel("A").getbbox()
    return img.crop(bbox) if bbox else img

def _fit_square(src, d):
    orig_w, orig_h = src.size
    scale = min(d / orig_w, d / orig_h)
    new_w, new_h = max(1, round(orig_w * scale)), max(1, round(orig_h * scale))
    resized = src.resize((new_w, new_h), Image.LANCZOS)
    canvas  = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    canvas.paste(resized, ((d - new_w) // 2, (d - new_h) // 2), resized)
    return canvas

def _save_ico(src, path, dims):
    frames = []
    for d in dims:
        frame = _fit_square(src, d)
        w, h  = frame.size
        flipped = frame.transpose(Image.FLIP_TOP_BOTTOM)
        rgba  = flipped.tobytes()
        bgra  = bytearray(len(rgba))
        for j in range(0, len(rgba), 4):
            bgra[j], bgra[j+1], bgra[j+2], bgra[j+3] = rgba[j+2], rgba[j+1], rgba[j], rgba[j+3]
        row_bytes = ((w + 31) // 32) * 4
        and_mask  = b'\x00' * (row_bytes * h)
        header = struct.pack("<IiiHHIIiiII", 40, w, h*2, 1, 32, 0,
                             len(bgra)+len(and_mask), 0, 0, 0, 0)
        frames.append((header, bytes(bgra), and_mask))
    count  = len(frames)
    offset = 6 + 16 * count
    with open(path, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, count))
        for d, (header, bgra, and_mask) in zip(dims, frames):
            data_size = len(header) + len(bgra) + len(and_mask)
            f.write(struct.pack("<BBBBHHII", d if d < 256 else 0, d if d < 256 else 0,
                                0, 0, 1, 32, data_size, offset))
            offset += data_size
        for header, bgra, and_mask in frames:
            f.write(header); f.write(bgra); f.write(and_mask)

# ── reusable widget helpers ────────────────────────────────────────────────────
def _btn(parent, text, cmd, bg=ACCENT, fg=TEXT, **kw):
    b = Label(parent, text=text, bg=bg, fg=fg,
              font=("Segoe UI", 10, "bold"), cursor="hand2",
              padx=18, pady=8, **kw)
    b.bind("<Button-1>", lambda e: cmd())
    b.bind("<Enter>",    lambda e: b.config(bg=ACCENT2))
    b.bind("<Leave>",    lambda e: b.config(bg=bg))
    return b

def _entry(parent, var, placeholder="", width=8):
    e = Entry(parent, textvariable=var, width=width,
              bg=CARD, fg=TEXT, insertbackground=TEXT,
              relief="flat", font=("Segoe UI", 10),
              highlightthickness=1, highlightbackground=BORDER,
              highlightcolor=ACCENT)
    if placeholder and not var.get():
        e.insert(0, placeholder)
        e.config(fg=SUBTEXT)
        def _focus_in(ev):
            if e.get() == placeholder:
                e.delete(0, END); e.config(fg=TEXT)
        def _focus_out(ev):
            if not e.get():
                e.insert(0, placeholder); e.config(fg=SUBTEXT)
        e.bind("<FocusIn>",  _focus_in)
        e.bind("<FocusOut>", _focus_out)
    return e

# ── file card ──────────────────────────────────────────────────────────────────
class FileCard(Frame):
    def __init__(self, parent, filepath, remove_cb):
        super().__init__(parent, bg=CARD, pady=6, padx=10)
        self.filepath  = filepath
        self._progress = 0

        name = os.path.basename(filepath)
        try:
            size = f"{os.path.getsize(filepath)/1024:.1f} KB"
        except Exception:
            size = ""

        # icon dot
        Label(self, text="●", bg=CARD, fg=ACCENT,
              font=("Segoe UI", 8)).pack(side=LEFT, padx=(0, 8))

        info = Frame(self, bg=CARD)
        info.pack(side=LEFT, fill=X, expand=True)
        Label(info, text=name, bg=CARD, fg=TEXT,
              font=("Segoe UI", 9, "bold"), anchor="w").pack(fill=X)
        self.sub = Label(info, text=size, bg=CARD, fg=SUBTEXT,
                         font=("Segoe UI", 8), anchor="w")
        self.sub.pack(fill=X)

        # thin progress bar
        self.bar_bg = Frame(self, bg=BORDER, height=3)
        self.bar_bg.pack(side=BOTTOM, fill=X, pady=(4, 0))
        self.bar    = Frame(self.bar_bg, bg=ACCENT, height=3, width=0)
        self.bar.place(x=0, y=0, relheight=1, relwidth=0)

        Label(self, text="✕", bg=CARD, fg=SUBTEXT,
              font=("Segoe UI", 10), cursor="hand2").pack(side=RIGHT, padx=(8, 0))
        self.children[list(self.children)[-1]].bind(
            "<Button-1>", lambda e: remove_cb(self))

        self.pack(fill=X, pady=2)

    def set_progress(self, pct, state="converting"):
        color = SUCCESS if state == "done" else ERROR if state == "error" else ACCENT2
        self.bar.place(relwidth=pct / 100)
        self.bar.config(bg=color)
        label = "✓ Done" if state == "done" else "✗ Error" if state == "error" else f"{pct:.0f}%"
        self.sub.config(text=label, fg=color)

# ── main app ───────────────────────────────────────────────────────────────────
class ImageConverterApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kairos Image Converter")
        self.geometry("860x620")
        self.minsize(640, 480)
        self.configure(bg=BG)
        self.cards: list[FileCard] = []
        self._build_ui()
        self.bind("<Configure>", self._on_resize)

    # ── layout ─────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.columnconfigure(0, weight=0, minsize=240)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()

    def _build_sidebar(self):
        sb = Frame(self, bg=SURFACE, width=240)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.columnconfigure(0, weight=1)

        # logo / title
        Label(sb, text="⚡ Kairos", bg=SURFACE, fg=ACCENT,
              font=("Segoe UI", 16, "bold")).pack(pady=(24, 2))
        Label(sb, text="Image Converter", bg=SURFACE, fg=SUBTEXT,
              font=("Segoe UI", 9)).pack(pady=(0, 20))

        Frame(sb, bg=BORDER, height=1).pack(fill=X, padx=16, pady=(0, 20))

        def section(label):
            Label(sb, text=label.upper(), bg=SURFACE, fg=SUBTEXT,
                  font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=16, pady=(12, 4))

        # format
        section("Output Format")
        self.fmt_var = StringVar(value="JPEG")
        fmt_frame = Frame(sb, bg=SURFACE)
        fmt_frame.pack(fill=X, padx=16)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("S.TCombobox", fieldbackground=CARD, background=CARD,
                        foreground=TEXT, selectbackground=CARD, selectforeground=TEXT,
                        arrowcolor=ACCENT)
        cb = ttk.Combobox(fmt_frame, textvariable=self.fmt_var, values=FORMATS,
                          state="readonly", style="S.TCombobox")
        cb.pack(fill=X)

        # resize
        section("Resize (px)")
        resize_row = Frame(sb, bg=SURFACE)
        resize_row.pack(fill=X, padx=16)
        self.width_var  = StringVar()
        self.height_var = StringVar()
        _entry(resize_row, self.width_var,  "W").pack(side=LEFT, fill=X, expand=True, padx=(0,4))
        Label(resize_row, text="×", bg=SURFACE, fg=SUBTEXT,
              font=("Segoe UI", 11)).pack(side=LEFT)
        _entry(resize_row, self.height_var, "H").pack(side=LEFT, fill=X, expand=True, padx=(4,0))

        # quality
        section("Quality")
        q_row = Frame(sb, bg=SURFACE)
        q_row.pack(fill=X, padx=16)
        self.quality_var = IntVar(value=85)
        self.q_label = Label(q_row, text="85", bg=SURFACE, fg=ACCENT,
                             font=("Segoe UI", 10, "bold"), width=3)
        self.q_label.pack(side=RIGHT)
        style.configure("Q.Horizontal.TScale", background=SURFACE, troughcolor=BORDER,
                        sliderlength=14, sliderrelief="flat")
        sc = ttk.Scale(q_row, from_=1, to=95, variable=self.quality_var,
                       orient=HORIZONTAL, style="Q.Horizontal.TScale",
                       command=lambda v: self.q_label.config(text=str(int(float(v)))))
        sc.pack(side=LEFT, fill=X, expand=True)

        # output dir
        section("Output Folder")
        self.out_var = StringVar(value="")
        out_row = Frame(sb, bg=SURFACE)
        out_row.pack(fill=X, padx=16)
        _entry(out_row, self.out_var, "Same as source", width=14).pack(
            side=LEFT, fill=X, expand=True, padx=(0, 4))
        folder_btn = Label(out_row, text="📁", bg=SURFACE, fg=ACCENT,
              font=("Segoe UI", 12), cursor="hand2")
        folder_btn.pack(side=LEFT)
        folder_btn.bind("<Button-1>", lambda e: self._browse_output())

        Frame(sb, bg=BORDER, height=1).pack(fill=X, padx=16, pady=20)

        # action buttons
        _btn(sb, "▶  Convert All", self._start_conversion).pack(
            fill=X, padx=16, pady=(0, 8))
        _btn(sb, "✕  Clear All", self._clear,
             bg=CARD).pack(fill=X, padx=16)

        # status counts
        self.stat_loaded    = StringVar(value="0")
        self.stat_converted = StringVar(value="0")
        self.stat_failed    = StringVar(value="0")
        Frame(sb, bg=BORDER, height=1).pack(fill=X, padx=16, pady=20)
        stats = Frame(sb, bg=SURFACE)
        stats.pack(fill=X, padx=16)
        for label, var, color in [
            ("Loaded",    self.stat_loaded,    TEXT),
            ("Converted", self.stat_converted, SUCCESS),
            ("Failed",    self.stat_failed,    ERROR),
        ]:
            col = Frame(stats, bg=SURFACE)
            col.pack(side=LEFT, expand=True)
            Label(col, textvariable=var, bg=SURFACE, fg=color,
                  font=("Segoe UI", 18, "bold")).pack()
            Label(col, text=label, bg=SURFACE, fg=SUBTEXT,
                  font=("Segoe UI", 7)).pack()

    def _build_main(self):
        main = Frame(self, bg=BG)
        main.grid(row=0, column=1, sticky="nsew", padx=(1, 0))
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        # drop zone
        self.drop_frame = Frame(main, bg=SURFACE, cursor="hand2",
                                highlightthickness=2, highlightbackground=BORDER)
        self.drop_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))
        self.drop_label = Label(
            self.drop_frame,
            text="⬇   Drop images here   ⬇\nor click to browse",
            bg=SURFACE, fg=ACCENT,
            font=("Segoe UI", 12, "bold"), pady=28
        )
        self.drop_label.pack(fill=X)
        for w in (self.drop_frame, self.drop_label):
            w.bind("<Button-1>", lambda e: self._browse())
            w.bind("<Enter>",    lambda e: self._drop_hover(True))
            w.bind("<Leave>",    lambda e: self._drop_hover(False))
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind("<<Drop>>",          self._on_drop)
        self.drop_frame.dnd_bind("<<DragEnter>>",     lambda e: self._drop_hover(True))
        self.drop_frame.dnd_bind("<<DragLeave>>",     lambda e: self._drop_hover(False))

        # scrollable file list
        list_outer = Frame(main, bg=BG)
        list_outer.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        list_outer.columnconfigure(0, weight=1)
        list_outer.rowconfigure(0, weight=1)

        canvas = Canvas(list_outer, bg=BG, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        vsb = Scrollbar(list_outer, orient=VERTICAL, command=canvas.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=vsb.set)

        self.card_frame = Frame(canvas, bg=BG)
        self._canvas_window = canvas.create_window((0, 0), window=self.card_frame, anchor="nw")

        self.card_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(self._canvas_window, width=e.width))
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self._canvas = canvas

        # global progress bar at bottom
        prog_frame = Frame(main, bg=BG)
        prog_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 12))
        prog_frame.columnconfigure(0, weight=1)
        style = ttk.Style()
        style.configure("G.Horizontal.TProgressbar", troughcolor=SURFACE,
                        background=ACCENT, bordercolor=BG, lightcolor=ACCENT,
                        darkcolor=ACCENT)
        self.progress = ttk.Progressbar(prog_frame, mode="determinate",
                                        style="G.Horizontal.TProgressbar")
        self.progress.grid(row=0, column=0, sticky="ew")
        self.status_var = StringVar(value="Ready")
        Label(prog_frame, textvariable=self.status_var, bg=BG, fg=SUBTEXT,
              font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w", pady=(2, 0))

    # ── responsiveness ─────────────────────────────────────────────────────────
    def _on_resize(self, event):
        if event.widget is self:
            # sidebar stays fixed at 240, main panel takes the rest
            pass  # grid weights handle it automatically

    def _drop_hover(self, active):
        color = ACCENT if active else BORDER
        self.drop_frame.config(highlightbackground=color)
        self.drop_label.config(fg=ACCENT2 if active else ACCENT)

    # ── file management ────────────────────────────────────────────────────────
    def _on_drop(self, event):
        paths = self.tk.splitlist(event.data)
        self._add_files([p for p in paths if os.path.isfile(p)])
        self._drop_hover(False)

    def _browse(self):
        paths = filedialog.askopenfilenames(
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.gif *.heic *.heif")])
        self._add_files(paths)

    def _browse_output(self):
        d = filedialog.askdirectory()
        if d:
            self.out_var.set(d)

    def _add_files(self, paths):
        existing = {c.filepath for c in self.cards}
        for p in paths:
            if p not in existing:
                card = FileCard(self.card_frame, p, self._remove_card)
                self.cards.append(card)
        self._update_stats()

    def _remove_card(self, card):
        card.destroy()
        self.cards.remove(card)
        self._update_stats()

    def _clear(self):
        for c in self.cards:
            c.destroy()
        self.cards.clear()
        self.progress["value"] = 0
        self.status_var.set("Ready")
        self._update_stats()

    def _update_stats(self):
        self.stat_loaded.set(str(len(self.cards)))

    # ── conversion ─────────────────────────────────────────────────────────────
    def _start_conversion(self):
        if not self.cards:
            messagebox.showwarning("No files", "Please add images first.")
            return
        threading.Thread(target=self._convert_all, daemon=True).start()

    def _convert_all(self):
        fmt     = self.fmt_var.get()
        quality = self.quality_var.get()
        total   = len(self.cards)
        done    = 0
        failed  = 0

        try:
            w = int(self.width_var.get())  if self.width_var.get().strip()  not in ("", "W") else None
            h = int(self.height_var.get()) if self.height_var.get().strip() not in ("", "H") else None
        except ValueError:
            messagebox.showerror("Invalid input", "Width and Height must be integers.")
            return

        for i, card in enumerate(self.cards):
            path = card.filepath
            try:
                out_dir = self.out_var.get() if self.out_var.get() not in ("", "Same as source") \
                          else os.path.dirname(path)
                os.makedirs(out_dir, exist_ok=True)
                name    = os.path.splitext(os.path.basename(path))[0]
                ext     = fmt.lower().replace("jpeg", "jpg")
                out_path = os.path.join(out_dir, f"{name}.{ext}")

                img = Image.open(path)

                if fmt == "ICO":
                    img = img.convert("RGBA")
                    img = _crop_transparent_padding(img)
                    orig_w, orig_h = img.size
                    if w or h:
                        new_w = w or int(orig_w * h / orig_h)
                        new_h = h or int(orig_h * w / orig_w)
                        dims  = [max(new_w, new_h)]
                    else:
                        max_dim = min(max(orig_w, orig_h), 256)
                        dims    = [s for s in ICO_SIZES if s <= max_dim]
                        if not dims or dims[-1] != max_dim:
                            dims.append(max_dim)
                    _save_ico(img, out_path, dims)
                else:
                    if img.mode in ("RGBA", "P") and fmt in ("JPEG", "HEIC"):
                        bg = Image.new("RGB", img.size, (255, 255, 255))
                        bg.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[3])
                        img = bg
                    if w or h:
                        orig_w, orig_h = img.size
                        new_w = w or int(orig_w * h / orig_h)
                        new_h = h or int(orig_h * w / orig_w)
                        img   = img.resize((new_w, new_h), Image.LANCZOS)
                    save_kw = {"quality": quality, "optimize": True} if fmt in ("JPEG", "WEBP") \
                              else {"quality": quality} if fmt == "HEIC" else {}
                    img.save(out_path, fmt, **save_kw)

                done += 1
                card.set_progress(100, "done")

            except Exception as e:
                failed += 1
                card.set_progress(100, "error")

            self.progress["value"] = (i + 1) / total * 100
            self.status_var.set(f"Converting {i+1}/{total}…")
            self.stat_converted.set(str(done))
            self.stat_failed.set(str(failed))

        self.status_var.set(f"Done — {done} converted, {failed} failed")

if __name__ == "__main__":
    app = ImageConverterApp()
    app.mainloop()
