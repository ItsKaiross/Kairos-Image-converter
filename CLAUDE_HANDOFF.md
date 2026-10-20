# Kairos Image Converter — copy-paste handoff for Claude

Paste everything below the divider into Claude. Give Claude access to `app.py`, `requirements.txt`, and `Image_Converter.spec` if you want it to implement the extraction using the original code.

---

I have an existing Python image converter called Kairos Image Converter. I want to reuse its entire image-processing workflow and backend with a different UI. Extract the processing into a reusable, headless Python package. Do not reproduce the existing Tkinter interface or its styling. My replacement UI will be supplied separately.

The following describes the current source code and the intended extraction. Proposed interfaces and improvements below are requirements for the refactor, not features that already exist.

## 1. Current project

- `app.py`: the entire application, including image helpers, Tkinter widgets, queue management, and batch processing.
- `requirements.txt`: `Pillow>=10.0.0`, `tkinterdnd2>=0.3.0`, `pillow-heif>=0.18.0`.
- `Image_Converter.spec`: PyInstaller configuration targeting `app.py`, including the two application icons and `console=False`.
- `kairos_icon.ico` and `kairos_icon.png`: desktop branding assets, not processing dependencies.
- `README.md`: project overview; use the source as the authority where descriptions differ.
- `build/` and `dist/`: generated desktop packaging artifacts.

There is currently no independent backend module, HTTP server, REST API, database, authentication, persistent job system, or command-line interface. The app processes local files and writes local output files. Its backend is currently embedded in `ImageConverterApp._convert_all()`.

## 2. Supported formats and defaults

- Output choices: JPEG, PNG, WEBP, BMP, TIFF, GIF, HEIC, ICO.
- Inputs are opened with Pillow after `register_heif_opener()` is called. Actual support depends on installed decoders and encoders.
- The current file picker filters JPG/JPEG, PNG, WEBP, BMP, TIFF, GIF, HEIC/HEIF. It omits ICO and `.tif`, although drag-and-drop does not impose that filter and the decoder may support them.
- Default output format: JPEG.
- Default quality: 85. The current slider offers 1–95, despite the README describing 0–100.
- Width and height are optional. Blank means unspecified.
- Blank output folder means each image's own source directory.
- JPEG output uses `.jpg`; other output extensions are the lowercase format name.

## 3. Actual current workflow

### Queue and job setup

1. Accept local file paths from the picker or drag-and-drop. Drop handling discards paths that are not files.
2. Deduplicate by exact path-string equality. Paths are not normalized or resolved before comparison.
3. Store queue items as `FileCard` widget instances. This coupling must be removed.
4. Prevent queue additions, removals, and clearing while conversion is running.
5. Reject an empty queue. Parse supplied dimensions as integers; positive dimensions are not currently enforced.
6. Start one daemon worker thread. Files are processed sequentially in queue order, not in parallel.
7. Snapshot the queued cards. Format, quality, and output folder are read from Tkinter state inside the worker; move all settings collection outside the backend worker during extraction.

### Per-image processing

1. Check the cancellation event before starting the next file.
2. Choose the configured output directory, or that file's source directory. Create the directory if needed.
3. Derive the output name from the source basename and target extension.
4. Avoid existing filenames with `_unique_path()`: use `photo.jpg`, then `photo (1).jpg`, `photo (2).jpg`, and so on. This also avoids overwriting the source when converting to the same format.
5. Open the image with `Image.open(path)` and call `img.load()`.
6. Apply the ICO-specific branch below, or the normal conversion branch.
7. Save the result and increment the success counter. On an exception, record the message for that file, increment the failure counter, and continue with the remaining files.
8. Update batch progress after each attempted file: `attempted / total * 100`. Failed attempts count toward progress.
9. Finish with success/failure totals or cancellation status.

### Normal conversion branch

- When the source mode is `RGBA` or `P` and the target is JPEG or HEIC, convert to RGBA and composite onto a white RGB background using the alpha channel.
- If only width is supplied, calculate height as `int(original_height * width / original_width)`.
- If only height is supplied, calculate width as `int(original_width * height / original_height)`.
- If both are supplied, resize to those exact dimensions. This can distort the image; the current code does not preserve aspect ratio in this case.
- Resize with Pillow's LANCZOS resampling.
- JPEG and WEBP save arguments: `quality=<selected quality>, optimize=True`.
- HEIC save arguments: `quality=<selected quality>`.
- PNG, BMP, TIFF, and GIF receive no extra save arguments.
- Animation and multiple TIFF pages are not preserved: there is no frame loop or `save_all` handling.

### ICO conversion branch

Preserve the custom ICO implementation unless a replacement is verified to produce equivalent usable multi-resolution icons.

1. Convert the source to RGBA.
2. Crop transparent padding using the alpha channel's bounding box. If all pixels are transparent, keep the original bounds.
3. With no requested dimensions, calculate `max_dim = min(max(cropped_width, cropped_height), 256)`.
4. Start with `[256, 128, 64, 48, 32, 16]`, keeping sizes at or below `max_dim`. The code then appends `max_dim` when the list is empty or its last element differs from `max_dim`. This can duplicate a standard size; fix this explicitly in the refactor.
5. With requested dimensions, calculate a missing dimension from the cropped source ratio, then generate a single square frame with side `max(new_width, new_height)`. The current implementation does not enforce the 256-pixel limit here; add validation.
6. For each selected size, resize the cropped image to fit inside a transparent square, preserving aspect ratio and centering the image. Unlike ordinary resizing, this branch always fits the source inside a square.
7. `_save_ico()` manually writes the ICO directory, 40-byte BITMAPINFOHEADER for each frame, bottom-up BGRA pixel bytes, and a zero-filled AND mask with rows padded to 32 bits. Each entry uses 32-bit pixels; a 256-pixel dimension is encoded as zero in the directory.

### Cancellation and progress

- Cancellation uses `threading.Event` and is cooperative between files.
- A file already being decoded, resized, or saved is allowed to finish. Previously written outputs remain on disk.
- Current per-file UI states include pending/converting/done/error, but the conversion loop only reports terminal done/error updates. There is no real percentage progress inside an image operation.
- Tkinter `self.after()` delivers result and progress updates to widgets. Replace this with plain data events or callbacks.
- Currently the UI does not retain structured output paths or a reusable result object. Add those to the extracted backend.

## 4. Remove the existing UI from the extracted backend

The backend must not import Tkinter, `tkinterdnd2`, or `PIL.ImageTk`, create a window, access widget values, or call `mainloop()`.

Exclude these presentation components from the backend:

- Theme colors, fonts, geometry, sidebar layout, drop zone, scroll canvas, progress widgets, and counters implemented as Tk variables.
- `_round_rect_points()`, `RoundedButton`, `PlaceholderEntry`, `ToolTip`, and `FileCard`.
- `_load_logo_photo()` and application icon-loading methods.
- Windows AppUserModelID and Win32 taskbar/window icon code.
- File/folder dialogs, drag-and-drop event parsing, hover effects, and message boxes.
- Tkinter-specific methods such as `_build_ui`, `_build_sidebar`, `_build_main`, `_drop_hover`, `_mark_error`, `_update_progress`, and `_on_conversion_done`. Preserve their useful data/state semantics through the new backend interface.

Do not delete `ImageConverterApp` wholesale before moving its useful logic: it currently owns input parsing, queue state, cancellation, batch iteration, and conversion.

The replacement UI should own file selection or uploads, previews, layout, controls, and displaying events/results. The backend should own validation, conversion, output naming, per-file outcomes, batch accounting, and cancellation checks.

## 5. Suggested backend structure and contract

Use a small Python package, for example:

```text
kairos_backend/
    __init__.py
    models.py       # options, file results, progress events, batch results
    converter.py    # one-image pipeline and format handling
    ico.py          # crop, square fitting, custom ICO writer
    batch.py        # sequential jobs, events, cancellation
    paths.py        # normalization and safe output naming
requirements-backend.txt
tests/
```

Retain Pillow and pillow-heif as backend dependencies. `tkinterdnd2` belongs only to a retained legacy UI. Use a currently compatible Python version and document the supported version after checking dependencies; do not rely on the README's Python 3.7 claim.

Suggested public API; finalize precise types during implementation:

```python
ConversionOptions(
    output_format="JPEG",
    quality=85,
    width=None,
    height=None,
    output_dir=None,
)

convert_image(source_path, options) -> ConversionResult

convert_batch(
    source_paths,
    options,
    on_event=None,
    cancel_event=None,
) -> BatchResult
```

- Options should be plain validated values, immutable for a running batch.
- A file result should include source path, output path on success, terminal status, and error details on failure.
- Events should identify the file and communicate start, success/failure, and batch progress. Include total, attempted, succeeded, and failed counts where appropriate.
- Batch results should include file results, counts, cancellation state, and how many files were not attempted.
- Callbacks run in the processing thread unless explicitly documented otherwise. The replacement UI is responsible for dispatching updates onto its own event loop.
- Keep the conversion service callable synchronously. A desktop adapter can run it on a worker; a server adapter can use a background job. Do not require a UI event loop.
- Do not invent an HTTP service merely to replace the UI. If the supplied UI is browser-based, add a thin adapter appropriate to its deployment and return job IDs/progress/output downloads. Browser uploads cannot be treated as arbitrary paths on the user's machine. Define upload storage and cleanup separately from the image engine.

## 6. Known issues to address deliberately

These are source-level findings, not runtime-verified defects or guarantees about installed codecs:

- Validate supported format names, quality bounds, positive dimensions, and output location before starting work.
- Clamp a proportionally computed dimension to at least one pixel.
- Validate ICO frame sizes within 1–256 and remove duplicate entries while keeping a deterministic order.
- Review `_fit_square()` alpha compositing: `canvas.paste(resized, position, resized)` uses the RGBA image as its own mask and can reduce partial alpha. Verify semitransparent edges and correct this if needed.
- Handle transparency and unsupported source color modes intentionally, including `LA` images, rather than assuming only `RGBA` and `P` need attention.
- Use context managers and close derived image objects appropriately; `img.load()` alone is not a universal guarantee of source-handle release for multi-frame formats.
- Current `_unique_path()` checks existence before writing; it does not reserve a filename atomically. Prevent collisions if multiple jobs/processes can share a destination.
- Consider temporary writes with cleanup and atomic final publication so failed conversions do not leave misleading partial output files.
- Decide and document metadata policy. The source does not explicitly transpose by EXIF orientation or preserve EXIF, ICC profiles, animation, or multiple pages.
- Verify HEIC output with the installed encoder; successful registration of the HEIF reader alone is not proof that encoding works.
- Normalize queue paths if reliable deduplication is required. The current string-based rule can accept aliases of the same file.
- Preserve the resize behavior described above unless a deliberate new resize mode is introduced and documented.

## 7. Acceptance criteria

1. Importing and using the backend works without a display, desktop assets, or Tkinter dependencies.
2. All eight output choices are represented, with useful errors when a required codec is unavailable.
3. A batch continues after one corrupt or unsupported image fails.
4. Successful results contain the actual output paths, including numeric suffixes.
5. Existing files and source images are not overwritten.
6. Tests cover ordinary conversion, alpha-to-white JPEG conversion, width-only/height-only/exact resizing, unique names, batch failure isolation, cancellation between files, and ICO frame sizes and transparency.
7. ICO output opens successfully and exposes the intended unique frame sizes.
8. Progress counts attempted files, including failures; it never claims measured per-image percentage progress.
9. Document codec limitations, single-frame behavior, metadata policy, and how the new UI calls the package.
10. Update packaging and dependency instructions to match the final entry point. The existing PyInstaller spec targets the old desktop UI and cannot simply be reused unchanged for a different app architecture.

Start by inspecting the supplied source, extract the backend, verify it with focused tests, and provide a minimal integration example for my replacement UI. Keep UI design work outside this extraction.
