import os
import sys
import threading
import struct
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image, ImageTk
from pillow_heif import register_heif_opener

register_heif_opener()

FORMATS   = ["JPEG", "PNG", "WEBP", "BMP", "TIFF", "GIF", "HEIC", "ICO"]
ICO_SIZES = [256, 128, 64, 48, 32, 16]

APP_DIR   = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
ICON_ICO  = os.path.join(APP_DIR, "kairos_icon.ico")
ICON_PNG  = os.path.join(APP_DIR, "kairos_icon.png")

# ── palette ────────────────────────────────────────────────────────────────────
BG        = "#0a0a12"
SURFACE   = "#14141f"
CARD      = "#181826"
CARD_HOV  = "#1e1e30"
BORDER    = "#26263a"
ACCENT    = "#8b5cf6"
ACCENT2   = "#a78bfa"
SUCCESS   = "#22c55e"
ERROR     = "#f43f5e"
TEXT      = "#f1f5f9"
SUBTEXT   = "#8b8ca3"

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

def _load_logo_photo(master, size=34, bg_rgb=(0x14, 0x14, 0x1f)):
    """Square app-icon glyph, cropped to its opaque bounds and composited
    onto the sidebar background so it reads cleanly at small sizes."""
    try:
        im = Image.open(ICON_PNG).convert("RGBA")
        bbox = im.getchannel("A").getbbox()
        if bbox:
            im = im.crop(bbox)
        im = im.resize((size, size), Image.LANCZOS)
        flat = Image.new("RGB", im.size, bg_rgb)
        flat.paste(im, mask=im.split()[3])
        return ImageTk.PhotoImage(flat, master=master)
    except Exception:
        return None

def _unique_path(path):
    """Never silently clobber an existing file (including the source itself)."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 1
    while True:
        candidate = f"{base} ({n}){ext}"
        if not os.path.exists(candidate):
            return candidate
        n += 1

# ── rounded-rect canvas button ────────────────────────────────────────────────
def _round_rect_points(x1, y1, x2, y2, r):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    return [
        x1 + r, y1,  x2 - r, y1,  x2, y1,  x2, y1 + r,
        x2, y2 - r,  x2, y2,  x2 - r, y2,  x1 + r, y2,
        x1, y2,  x1, y2 - r,  x1, y1 + r,  x1, y1,
    ]

class RoundedButton(Canvas):
    def __init__(self, parent, text, command, fill=ACCENT, hover=ACCENT2,
                 fg=TEXT, height=38, radius=10, font=("Segoe UI", 10, "bold")):
        super().__init__(parent, bg=parent["bg"], highlightthickness=0, height=height, bd=0)
        self.command   = command
        self.text      = text
        self.fill      = fill
        self.hover     = hover
        self.fg        = fg
        self.radius    = radius
        self.font      = font
        self._enabled  = True
        self._shape    = None
        self.configure(cursor="hand2")
        self.bind("<Configure>", self._draw)
        self.bind("<Button-1>",  self._on_click)
        self.bind("<Enter>",     lambda e: self._enabled and self._shape and
                                  self.itemconfig(self._shape, fill=self.hover))
        self.bind("<Leave>",     lambda e: self._enabled and self._shape and
                                  self.itemconfig(self._shape, fill=self.fill))

    def _draw(self, event=None):
        self.delete("all")
        w = self.winfo_width() or 140
        h = self.winfo_height()
        fill = self.fill if self._enabled else BORDER
        fg   = self.fg if self._enabled else SUBTEXT
        pts  = _round_rect_points(1, 1, w - 1, h - 1, self.radius)
        self._shape = self.create_polygon(pts, smooth=True, fill=fill, outline="")
        self.create_text(w / 2, h / 2, text=self.text, fill=fg, font=self.font)

    def _on_click(self, event):
        if self._enabled and self.command:
            self.command()

    def set_text(self, text):
        self.text = text
        self._draw()

    def set_style(self, fill, hover=None):
        self.fill  = fill
        self.hover = hover or fill
        self._draw()

    def set_enabled(self, enabled):
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

# ── placeholder-aware entry ───────────────────────────────────────────────────
class PlaceholderEntry(Entry):
    """Tracks placeholder state explicitly instead of comparing text, so a
    real value that happens to match the placeholder string is never mistaken
    for 'empty'."""
    def __init__(self, parent, var, placeholder="", width=8, **kw):
        self._var         = var
        self._placeholder = placeholder
        self._is_placeholder = False
        super().__init__(parent, textvariable=var, width=width,
                          bg=CARD, fg=TEXT, insertbackground=TEXT,
                          relief="flat", font=("Segoe UI", 10),
                          highlightthickness=1, highlightbackground=BORDER,
                          highlightcolor=ACCENT, **kw)
        if placeholder and not var.get():
            self._show_placeholder()
        self.bind("<FocusIn>",  self._focus_in)
        self.bind("<FocusOut>", self._focus_out)

    def _show_placeholder(self):
        self._is_placeholder = True
        self._var.set(self._placeholder)
        self.config(fg=SUBTEXT)

    def _focus_in(self, event):
        if self._is_placeholder:
            self._var.set("")
            self.config(fg=TEXT)
            self._is_placeholder = False

    def _focus_out(self, event):
        if not self._var.get():
            self._show_placeholder()

    def value(self):
        return "" if self._is_placeholder else self._var.get().strip()

    def set_value(self, text):
        self._is_placeholder = False
        self.config(fg=TEXT)
        self._var.set(text)

# ── hover tooltip (used to surface conversion errors) ─────────────────────────
class ToolTip:
    def __init__(self, widget, text_getter):
        self.widget = widget
        self.text_getter = text_getter
        self.tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event):
        text = self.text_getter()
        if not text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        Label(self.tip, text=text, bg="#20202f", fg=ERROR, font=("Segoe UI", 8),
              padx=8, pady=5, wraplength=280, justify="left",
              highlightthickness=1, highlightbackground=BORDER).pack()

    def _hide(self, event):
        if self.tip:
            self.tip.destroy()
            self.tip = None

# ── file card ──────────────────────────────────────────────────────────────────
class FileCard(Frame):
    def __init__(self, parent, filepath, remove_cb):
        super().__init__(parent, bg=CARD, pady=8, padx=0)
        self.filepath  = filepath
        self.error_msg = None

        name = os.path.basename(filepath)
        try:
            size = f"{os.path.getsize(filepath)/1024:.1f} KB"
        except OSError:
            size = ""

        # status accent bar
        self.accent = Frame(self, bg=SUBTEXT, width=3)
        self.accent.pack(side=LEFT, fill=Y, padx=(0, 10))

        info = Frame(self, bg=CARD)
        info.pack(side=LEFT, fill=X, expand=True)
        Label(info, text=name, bg=CARD, fg=TEXT,
              font=("Segoe UI", 9, "bold"), anchor="w").pack(fill=X)
        self.sub = Label(info, text=size, bg=CARD, fg=SUBTEXT,
                         font=("Segoe UI", 8), anchor="w")
        self.sub.pack(fill=X)

        # thin progress bar
        self.bar_bg = Frame(self, bg=BORDER, height=3)
        self.bar_bg.pack(side=BOTTOM, fill=X, pady=(6, 0))
        self.bar    = Frame(self.bar_bg, bg=ACCENT, height=3, width=0)
        self.bar.place(x=0, y=0, relheight=1, relwidth=0)

        self.close_btn = Label(self, text="✕", bg=CARD, fg=SUBTEXT,
                                font=("Segoe UI", 10), cursor="hand2", padx=4)
        self.close_btn.pack(side=RIGHT, padx=(8, 10))
        self.close_btn.bind("<Button-1>", lambda e: remove_cb(self))
        self.close_btn.bind("<Enter>", lambda e: self.close_btn.config(fg=ERROR))
        self.close_btn.bind("<Leave>", lambda e: self.close_btn.config(fg=SUBTEXT))

        ToolTip(self, lambda: self.error_msg)

        self.pack(fill=X, pady=3)

    def set_progress(self, pct, state="converting"):
        color = SUCCESS if state == "done" else ERROR if state == "error" else ACCENT2
        self.bar.place(relwidth=pct / 100)
        self.bar.config(bg=color)
        self.accent.config(bg=color)
        label = "✓ Done" if state == "done" else "✗ Error — hover for details" if state == "error" else f"{pct:.0f}%"
        self.sub.config(text=label, fg=color)

# ── main app ───────────────────────────────────────────────────────────────────
class ImageConverterApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kairos Image Converter")
        self.geometry("880x640")
        self.minsize(640, 480)
        self.configure(bg=BG)
        self._set_app_icon()
        self.cards: list[FileCard] = []
        self._converting    = False
        self._cancel_event  = threading.Event()
        self._build_ui()

    def _set_app_icon(self):
        try:
            self.iconbitmap(ICON_ICO)
        except Exception:
            pass
        try:
            self._icon_img = PhotoImage(file=ICON_PNG)
            self.iconphoto(True, self._icon_img)
        except Exception:
            pass

    # ── layout ─────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.columnconfigure(0, weight=0, minsize=250)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()

    def _build_sidebar(self):
        sb = Frame(self, bg=SURFACE, width=250)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.columnconfigure(0, weight=1)

        # logo / title
        logo_row = Frame(sb, bg=SURFACE)
        logo_row.pack(pady=(26, 2))
        self._logo_img = _load_logo_photo(self, size=34)
        if self._logo_img:
            Label(logo_row, image=self._logo_img, bg=SURFACE).pack(side=LEFT, padx=(0, 8))
        Label(logo_row, text="Kairos", bg=SURFACE, fg=ACCENT,
              font=("Segoe UI", 17, "bold")).pack(side=LEFT)
        Label(sb, text="Image Converter", bg=SURFACE, fg=SUBTEXT,
              font=("Segoe UI", 9)).pack(pady=(0, 22))

        Frame(sb, bg=BORDER, height=1).pack(fill=X, padx=18, pady=(0, 18))

        def section(label):
            Label(sb, text=label.upper(), bg=SURFACE, fg=SUBTEXT,
                  font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=18, pady=(12, 5))

        # format
        section("Output Format")
        self.fmt_var = StringVar(value="JPEG")
        fmt_frame = Frame(sb, bg=SURFACE)
        fmt_frame.pack(fill=X, padx=18)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("S.TCombobox", fieldbackground=CARD, background=CARD,
                        foreground=TEXT, selectbackground=CARD, selectforeground=TEXT,
                        arrowcolor=ACCENT, bordercolor=BORDER, lightcolor=CARD, darkcolor=CARD)
        style.map("S.TCombobox",
                  fieldbackground=[("readonly", CARD)],
                  foreground=[("readonly", TEXT)],
                  selectbackground=[("readonly", CARD)],
                  selectforeground=[("readonly", TEXT)])
        # the popdown list is a plain Listbox that ignores ttk styles entirely —
        # it must be themed through the Tk option database instead.
        self.option_add("*TCombobox*Listbox.background", CARD)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.option_add("*TCombobox*Listbox.selectForeground", TEXT)
        self.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))
        cb = ttk.Combobox(fmt_frame, textvariable=self.fmt_var, values=FORMATS,
                          state="readonly", style="S.TCombobox")
        cb.pack(fill=X, ipady=3)

        # resize
        section("Resize (px)")
        resize_row = Frame(sb, bg=SURFACE)
        resize_row.pack(fill=X, padx=18)
        self.width_var  = StringVar()
        self.height_var = StringVar()
        self.width_entry  = PlaceholderEntry(resize_row, self.width_var, "W")
        self.width_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 4), ipady=4)
        Label(resize_row, text="×", bg=SURFACE, fg=SUBTEXT,
              font=("Segoe UI", 11)).pack(side=LEFT)
        self.height_entry = PlaceholderEntry(resize_row, self.height_var, "H")
        self.height_entry.pack(side=LEFT, fill=X, expand=True, padx=(4, 0), ipady=4)

        # quality
        section("Quality")
        q_row = Frame(sb, bg=SURFACE)
        q_row.pack(fill=X, padx=18)
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
        out_row.pack(fill=X, padx=18)
        self.out_entry = PlaceholderEntry(out_row, self.out_var, "Same as source", width=14)
        self.out_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 4), ipady=4)
        folder_btn = Label(out_row, text="📁", bg=SURFACE, fg=ACCENT,
              font=("Segoe UI", 12), cursor="hand2")
        folder_btn.pack(side=LEFT)
        folder_btn.bind("<Button-1>", lambda e: self._browse_output())

        Frame(sb, bg=BORDER, height=1).pack(fill=X, padx=18, pady=22)

        # action buttons
        self.convert_btn = RoundedButton(sb, "▶  Convert All", self._start_conversion,
                                          fill=ACCENT, hover=ACCENT2)
        self.convert_btn.pack(fill=X, padx=18, pady=(0, 10))
        self.clear_btn = RoundedButton(sb, "✕  Clear All", self._clear,
                                        fill=CARD, hover=CARD_HOV)
        self.clear_btn.pack(fill=X, padx=18)

        # status counts
        self.stat_loaded    = StringVar(value="0")
        self.stat_converted = StringVar(value="0")
        self.stat_failed    = StringVar(value="0")
        Frame(sb, bg=BORDER, height=1).pack(fill=X, padx=18, pady=22)
        stats = Frame(sb, bg=SURFACE)
        stats.pack(fill=X, padx=18)
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

    def _drop_hover(self, active):
        if self._converting:
            return
        color = ACCENT if active else BORDER
        self.drop_frame.config(highlightbackground=color)
        self.drop_label.config(fg=ACCENT2 if active else ACCENT)

    # ── file management ────────────────────────────────────────────────────────
    def _on_drop(self, event):
        if self._converting:
            return
        paths = self.tk.splitlist(event.data)
        self._add_files([p for p in paths if os.path.isfile(p)])
        self._drop_hover(False)

    def _browse(self):
        if self._converting:
            return
        paths = filedialog.askopenfilenames(
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.gif *.heic *.heif")])
        self._add_files(paths)

    def _browse_output(self):
        d = filedialog.askdirectory()
        if d:
            self.out_entry.set_value(d)

    def _add_files(self, paths):
        existing = {c.filepath for c in self.cards}
        for p in paths:
            if p not in existing:
                card = FileCard(self.card_frame, p, self._remove_card)
                self.cards.append(card)
                existing.add(p)
        self._update_stats()

    def _remove_card(self, card):
        if self._converting:
            return
        card.destroy()
        self.cards.remove(card)
        self._update_stats()

    def _clear(self):
        if self._converting:
            return
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
        if self._converting:
            # button is currently in "Cancel" mode
            self._cancel_event.set()
            self.status_var.set("Cancelling…")
            return

        if not self.cards:
            messagebox.showwarning("No files", "Please add images first.")
            return

        w_str = self.width_entry.value()
        h_str = self.height_entry.value()
        try:
            w = int(w_str) if w_str else None
            h = int(h_str) if h_str else None
        except ValueError:
            messagebox.showerror("Invalid input", "Width and Height must be integers.")
            return

        self._converting   = True
        self._cancel_event = threading.Event()
        self.convert_btn.set_text("⏹  Cancel")
        self.convert_btn.set_style(ERROR, "#ff6b81")
        self.clear_btn.set_enabled(False)
        self._drop_hover(False)
        self.drop_label.config(text="Conversion in progress…", fg=SUBTEXT)
        self.drop_frame.config(cursor="arrow")
        self.stat_converted.set("0")
        self.stat_failed.set("0")

        threading.Thread(target=self._convert_all, args=(w, h), daemon=True).start()

    def _convert_all(self, w, h):
        fmt     = self.fmt_var.get()
        quality = self.quality_var.get()
        cards   = list(self.cards)
        total   = len(cards)
        done    = 0
        failed  = 0
        cancelled = False
        out_dir_setting = self.out_entry.value()

        for i, card in enumerate(cards):
            if self._cancel_event.is_set():
                cancelled = True
                break

            path = card.filepath
            try:
                out_dir = out_dir_setting or os.path.dirname(path)
                os.makedirs(out_dir, exist_ok=True)
                name    = os.path.splitext(os.path.basename(path))[0]
                ext     = fmt.lower().replace("jpeg", "jpg")
                out_path = _unique_path(os.path.join(out_dir, f"{name}.{ext}"))

                img = Image.open(path)
                img.load()  # decode now and release the source file handle

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
                        rgba = img.convert("RGBA")
                        bg   = Image.new("RGB", img.size, (255, 255, 255))
                        bg.paste(rgba, mask=rgba.split()[3])
                        img  = bg
                    if w or h:
                        orig_w, orig_h = img.size
                        new_w = w or int(orig_w * h / orig_h)
                        new_h = h or int(orig_h * w / orig_w)
                        img   = img.resize((new_w, new_h), Image.LANCZOS)
                    save_kw = {"quality": quality, "optimize": True} if fmt in ("JPEG", "WEBP") \
                              else {"quality": quality} if fmt == "HEIC" else {}
                    img.save(out_path, fmt, **save_kw)

                done += 1
                self.after(0, card.set_progress, 100, "done")

            except Exception as e:
                failed += 1
                self.after(0, self._mark_error, card, str(e))

            pct = (i + 1) / total * 100
            self.after(0, self._update_progress, pct, i + 1, total, done, failed)

        self.after(0, self._on_conversion_done, done, failed, cancelled)

    def _mark_error(self, card, msg):
        card.error_msg = msg
        card.set_progress(100, "error")

    def _update_progress(self, pct, i, total, done, failed):
        self.progress["value"] = pct
        self.status_var.set(f"Converting {i}/{total}…")
        self.stat_converted.set(str(done))
        self.stat_failed.set(str(failed))

    def _on_conversion_done(self, done, failed, cancelled):
        self._converting = False
        self.convert_btn.set_text("▶  Convert All")
        self.convert_btn.set_style(ACCENT, ACCENT2)
        self.clear_btn.set_enabled(True)
        self.drop_label.config(text="⬇   Drop images here   ⬇\nor click to browse", fg=ACCENT)
        self.drop_frame.config(cursor="hand2")
        self.status_var.set("Cancelled" if cancelled else f"Done — {done} converted, {failed} failed")

if __name__ == "__main__":
    app = ImageConverterApp()
    app.iconbitmap("kairos_icon.ico")
    app.mainloop()
