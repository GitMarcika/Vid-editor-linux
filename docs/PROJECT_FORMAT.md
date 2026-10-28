# Vid Editor project format

Project extension: `.vedproj`  
Encoding: UTF-8 JSON  
Current format version: 1

A project stores edit state and references source media files. It does **not** embed or copy the videos.

## Top-level structure

```json
{
  "format": "vid-editor-project",
  "version": 1,
  "raw_cutter": {},
  "assembly": {
    "clips": [],
    "text_overlays": []
  }
}
```

## Raw Cutter state

When a source is loaded, the section contains:

```json
{
  "source_video": "C:/media/source.mp4",
  "trim_start_ms": 1250,
  "trim_end_ms": 8000,
  "crop": {
    "x": 100,
    "y": 50,
    "width": 1280,
    "height": 720
  }
}
```

All timeline values are stored as integer milliseconds. Crop coordinates and dimensions are stored in source-video pixels.

## Assembly state

The schema reserves two arrays from version 1:

- `clips`: ordered video clip objects
- `text_overlays`: text overlay objects

The timeline and text-editor phases extend the contents of these objects without changing the top-level project format.

## Media lookup on project load

For every referenced video, Vid Editor tries:

1. the stored path;
2. the project directory plus a relative stored path;
3. a file with the same name directly in the project directory;
4. a recursive filename search below the project directory;
5. manual file location by the user.

This allows a project and its media folder to be moved together and still be recoverable.

## Save safety

Projects are written to a temporary file first and atomically replaced only after the JSON payload has been written successfully.

## Text overlay object

Phase 6 stores each overlay as a global-timeline object:

```json
{
  "id": "stable-overlay-id",
  "text": "Example caption",
  "start_ms": 1200,
  "end_ms": 5200,
  "x_norm": 0.42,
  "y_norm": 0.68,
  "font_family": "Arial",
  "font_size": 28,
  "text_color": "#ffffff",
  "background_enabled": true,
  "background_color": "#000000",
  "background_opacity": 170,
  "background_padding": 8,
  "outline_enabled": false,
  "outline_color": "#000000",
  "outline_width": 2,
  "shadow_enabled": false,
  "shadow_color": "#000000",
  "shadow_opacity": 160,
  "shadow_blur": 8,
  "shadow_offset_x": 3,
  "shadow_offset_y": 3
}
```

- `start_ms` / `end_ms` use the assembled video's global timeline.
- `x_norm` / `y_norm` are normalized preview coordinates from 0.0 to 1.0.
- The list is sorted by Start time in the editor.
- Styling fields are part of the same overlay object. Opacity values are stored as 0-255 alpha values; positions remain normalized.
