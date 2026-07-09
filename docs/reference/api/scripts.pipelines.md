# `scripts.pipelines` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `scripts/pipelines/_config.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `read_runtime_key` | `(key, env_override=…)` | Read a key from ~/.jarvis-v2/config/runtime.json. | [src](../../../scripts/pipelines/_config.py#L12) |

## `scripts/pipelines/jarvis_audio_pipeline.py`
_Jarvis Audio Pipeline for TikTok videos._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `generate_voiceover` | `(text, voice, output_path)` | Generate TTS voiceover using edge-tts. | [src](../../../scripts/pipelines/jarvis_audio_pipeline.py#L18) |
| function | `generate_ambient` | `(duration, sample_rate=…, output_path=…)` | Generate a cosmic/ambient background sound. | [src](../../../scripts/pipelines/jarvis_audio_pipeline.py#L31) |
| function | `mix_audio` | `(voice_path, ambient_path, output_path, voice_vol=…, ambient_vol=…)` | Mix voice and ambient using ffmpeg. | [src](../../../scripts/pipelines/jarvis_audio_pipeline.py#L68) |
| function | `merge_audio_video` | `(video_path, audio_path, output_path)` | Merge audio track with video using ffmpeg. | [src](../../../scripts/pipelines/jarvis_audio_pipeline.py#L85) |
| function | `full_pipeline` | `(video_path, text=…, voice=…, ambient_duration=…, voice_vol=…, ambient_vol=…, output_path=…)` | Run the full audio pipeline: voiceover + ambient → mix → merge with video. | [src](../../../scripts/pipelines/jarvis_audio_pipeline.py#L103) |

## `scripts/pipelines/jarvis_full_pipeline.py`
_Jarvis Full TikTok Pipeline_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `upload_image` | `(image_path, comfy_url=…)` | Upload image to ComfyUI and return server-side filename. | [src](../../../scripts/pipelines/jarvis_full_pipeline.py#L39) |
| function | `submit_workflow` | `(workflow, comfy_url=…)` | Submit workflow to ComfyUI queue, return prompt_id. | [src](../../../scripts/pipelines/jarvis_full_pipeline.py#L52) |
| function | `wait_for_completion` | `(prompt_id, comfy_url=…, timeout=…, poll=…)` | Poll /history until prompt completes. | [src](../../../scripts/pipelines/jarvis_full_pipeline.py#L61) |
| function | `find_output` | `(outputs, key=…)` | Find output filename and subfolder from ComfyUI outputs. | [src](../../../scripts/pipelines/jarvis_full_pipeline.py#L79) |
| function | `download_output` | `(filename, subfolder, dest_path, comfy_url=…)` | Download/copy output from ComfyUI. | [src](../../../scripts/pipelines/jarvis_full_pipeline.py#L90) |
| function | `build_sdxl_workflow` | `(prompt, negative, width, height, steps, output_prefix)` | SDXL text-to-image workflow. | [src](../../../scripts/pipelines/jarvis_full_pipeline.py#L113) |
| function | `generate_sdxl_image` | `(prompt, negative=…, width=…, height=…, steps=…, comfy_url=…)` | Generate image with SDXL, return local file path. | [src](../../../scripts/pipelines/jarvis_full_pipeline.py#L174) |
| function | `build_svd_workflow` | `(image_name, width, height, frames, fps, motion, steps, output_prefix)` | SVD img2vid workflow. | [src](../../../scripts/pipelines/jarvis_full_pipeline.py#L205) |
| function | `generate_svd_video` | `(image_path, width=…, height=…, frames=…, fps=…, motion=…, steps=…, comfy_url=…)` | Animate image with SVD, return video file path. | [src](../../../scripts/pipelines/jarvis_full_pipeline.py#L272) |
| function | `loop_video` | `(video_path, output_path, loop_count=…)` | Loop a video N times using FFmpeg stream_loop. Returns output path. | [src](../../../scripts/pipelines/jarvis_full_pipeline.py#L341) |
| function | `add_audio` | `(video_path, text, output_path, voice=…, ambient_vol=…)` | Add TTS voiceover + ambient audio using jarvis_audio_pipeline.py. | [src](../../../scripts/pipelines/jarvis_full_pipeline.py#L367) |
| function | `add_text_to_video` | `(video_path, text, output_path, font_size=…)` | Add centered text overlay to video using FFmpeg drawtext filter. | [src](../../../scripts/pipelines/jarvis_full_pipeline.py#L395) |
| function | `run_full_pipeline` | `(prompt, text, output_path=…, sdxl_steps=…, svd_frames=…, svd_fps=…, svd_motion=…, svd_steps=…, width=…, height=…, loop_count=…, voice=…, add_voice=…, comfy_url=…)` | Full pipeline: SDXL → SVD → loop → audio → text overlay → final video. | [src](../../../scripts/pipelines/jarvis_full_pipeline.py#L479) |
| function | `run_batch_pipeline` | `(items, output_dir=…, **kwargs)` | Run full pipeline for multiple (prompt, text) pairs. | [src](../../../scripts/pipelines/jarvis_full_pipeline.py#L564) |

## `scripts/pipelines/jarvis_json2video_pipeline.py`
_JSON2Video pipeline — creates TikTok-style videos via json2video.com API._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_headers` | `()` | — | [src](../../../scripts/pipelines/jarvis_json2video_pipeline.py#L36) |
| function | `_post` | `(body)` | — | [src](../../../scripts/pipelines/jarvis_json2video_pipeline.py#L62) |
| function | `_get_status` | `(project_id)` | — | [src](../../../scripts/pipelines/jarvis_json2video_pipeline.py#L73) |
| function | `_download` | `(url, output_path)` | — | [src](../../../scripts/pipelines/jarvis_json2video_pipeline.py#L84) |
| function | `_build_movie` | `(text, bg_color=…, text_color=…, bg_image_url=…, duration=…, draft=…)` | Build a json2video movie payload for a TikTok text-overlay video. | [src](../../../scripts/pipelines/jarvis_json2video_pipeline.py#L94) |
| function | `generate_tiktok_video` | `(text, output_path, slot=…, bg_image_url=…, duration=…, draft=…, poll_interval=…, timeout=…)` | Generate a TikTok text-overlay video via json2video. | [src](../../../scripts/pipelines/jarvis_json2video_pipeline.py#L161) |
| function | `_cli` | `()` | — | [src](../../../scripts/pipelines/jarvis_json2video_pipeline.py#L236) |

## `scripts/pipelines/jarvis_kling_pipeline.py`
_Kling AI video generation pipeline — direct API integration._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_build_jwt` | `(access_key, secret_key, exp_seconds=…)` | Build a HS256 JWT token for Kling API auth. | [src](../../../scripts/pipelines/jarvis_kling_pipeline.py#L28) |
| function | `_auth_headers` | `()` | — | [src](../../../scripts/pipelines/jarvis_kling_pipeline.py#L55) |
| function | `generate_text_to_video` | `(prompt, output_path, model=…, duration=…, aspect_ratio=…, cfg_scale=…, mode=…, poll_interval=…, timeout=…)` | Generate a video from a text prompt via Kling API. | [src](../../../scripts/pipelines/jarvis_kling_pipeline.py#L70) |
| function | `generate_image_to_video` | `(image_path, output_path, prompt=…, model=…, duration=…, cfg_scale=…, mode=…, poll_interval=…, timeout=…)` | Generate a video from an image via Kling API. | [src](../../../scripts/pipelines/jarvis_kling_pipeline.py#L122) |
| function | `_poll_and_download` | `(task_id, output_path, endpoint, poll_interval, timeout)` | Poll task until complete, download video to output_path. | [src](../../../scripts/pipelines/jarvis_kling_pipeline.py#L177) |
| function | `_download_video` | `(url, output_path)` | Download video from URL to output_path. | [src](../../../scripts/pipelines/jarvis_kling_pipeline.py#L218) |
| function | `generate_tiktok_video` | `(prompt, output_path, duration=…, mode=…)` | Convenience wrapper: text → 9:16 vertical TikTok video. | [src](../../../scripts/pipelines/jarvis_kling_pipeline.py#L234) |
| function | `_cli` | `()` | — | [src](../../../scripts/pipelines/jarvis_kling_pipeline.py#L256) |

## `scripts/pipelines/jarvis_piapi_pipeline.py`
_PiAPI.ai video generation pipeline — Kling AI via PiAPI proxy._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_headers` | `()` | — | [src](../../../scripts/pipelines/jarvis_piapi_pipeline.py#L27) |
| function | `_post` | `(endpoint, body)` | — | [src](../../../scripts/pipelines/jarvis_piapi_pipeline.py#L41) |
| function | `_get` | `(endpoint)` | — | [src](../../../scripts/pipelines/jarvis_piapi_pipeline.py#L52) |
| function | `_download` | `(url, output_path)` | Download a file from url to output_path. | [src](../../../scripts/pipelines/jarvis_piapi_pipeline.py#L62) |
| function | `_submit_task` | `(body)` | Submit a task. Returns task_id or raises on error. | [src](../../../scripts/pipelines/jarvis_piapi_pipeline.py#L76) |
| function | `_poll_task` | `(task_id, poll_interval=…, timeout=…)` | Poll until task is completed/failed. Returns final data dict. | [src](../../../scripts/pipelines/jarvis_piapi_pipeline.py#L87) |
| function | `_extract_video_url` | `(data)` | Extract watermark-free video URL from completed task data. | [src](../../../scripts/pipelines/jarvis_piapi_pipeline.py#L105) |
| function | `generate_text_to_video` | `(prompt, output_path, duration=…, aspect_ratio=…, mode=…, poll_interval=…, timeout=…)` | Generate video from text prompt via PiAPI Kling. | [src](../../../scripts/pipelines/jarvis_piapi_pipeline.py#L136) |
| function | `generate_image_to_video` | `(image_path, output_path, prompt=…, duration=…, mode=…, poll_interval=…, timeout=…)` | Generate video from an image via PiAPI Kling. | [src](../../../scripts/pipelines/jarvis_piapi_pipeline.py#L175) |
| function | `generate_tiktok_video` | `(prompt, output_path, duration=…, mode=…)` | Text → 9:16 TikTok video via PiAPI Kling. | [src](../../../scripts/pipelines/jarvis_piapi_pipeline.py#L219) |
| function | `_cli` | `()` | — | [src](../../../scripts/pipelines/jarvis_piapi_pipeline.py#L240) |

## `scripts/pipelines/jarvis_pollinations_pipeline.py`
_Jarvis TikTok pipeline — ComfyUI-free._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `generate_base_image` | `(*, prompt, width=…, height=…, model=…, seed=…, enhance=…)` | Generate a base image via pollinations.ai. Returns saved path. | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L40) |
| function | `build_zoom_video` | `(*, image_path, duration=…, zoom_start=…, zoom_end=…, fps=…, output_path=…)` | Slow-zoom animation from a still image. No GPU, bounded RAM. | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L62) |
| function | `build_crossfade_video` | `(*, image_paths, duration=…, fps=…, crossfade_duration=…, output_path=…)` | Multi-image crossfade video from N images. Each image gets equal screen time | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L107) |
| function | `_load_uploaded_paths` | `()` | Load set of already-uploaded video paths. | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L165) |
| function | `_mark_uploaded` | `(path)` | Mark a video path as uploaded. | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L176) |
| function | `is_already_uploaded` | `(path)` | Check if a video has already been uploaded. | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L186) |
| function | `build_ambient_background` | `(*, duration, sample_rate=…, volume=…, output_path=…)` | Generate a gentle ambient background drone (sine pad + filtered noise). | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L193) |
| function | `apply_background_music` | `(*, video_path, duration=…, volume=…, output_path=…)` | Overlay a gentle ambient background drone on the video. | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L239) |
| function | `_render_ai_label_png` | `(*, canvas_w, canvas_h, label=…)` | Render a small 'AI-genereret' badge in the top-right corner. | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L287) |
| function | `apply_ai_label` | `(*, video_path, output_path=…, label=…)` | Add a small 'AI-genereret' badge overlay in the top-right corner. | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L370) |
| function | `_render_text_png` | `(text, *, canvas_w, canvas_h, position=…, font_size=…)` | Render wrapped text to a transparent PNG via PIL (no ImageMagick). | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L409) |
| function | `add_text_overlay` | `(*, video_path, text, output_path=…, font_size=…, position=…)` | Burn a text overlay onto the video using PIL-rendered PNG (no ImageMagick). | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L488) |
| function | `_get_elevenlabs_key` | `()` | — | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L535) |
| function | `_synthesize_elevenlabs` | `(text)` | Generate MP3 via ElevenLabs API. Returns path to temp file. | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L544) |
| function | `add_voice` | `(*, video_path, text, output_path=…, voice=…)` | Add a TTS voiceover via ElevenLabs. Returns path with audio. | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L564) |
| function | `run_pipeline` | `(*, prompt, text, output_path=…, image_model=…, width=…, height=…, duration=…, zoom_start=…, zoom_end=…, fps=…, add_tts=…, voice=…, seed=…, enhance_prompt=…, keep_intermediates=…, text_position=…, video_style=…, multi_images=…, crossfade_duration=…, add_background_music=…, add_ai_label=…)` | Full pipeline returning dict with paths + timings. | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L627) |
| function | `main` | `()` | — | [src](../../../scripts/pipelines/jarvis_pollinations_pipeline.py#L802) |

## `scripts/pipelines/jarvis_svd_pipeline.py`
_Jarvis SVD Video Pipeline_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_build_svd_workflow` | `(image_name, width, height, frames, fps, motion, steps, output_prefix)` | Build ComfyUI prompt JSON for SVD img2vid. | [src](../../../scripts/pipelines/jarvis_svd_pipeline.py#L44) |
| function | `_upload_image` | `(image_path, comfy_url=…)` | Upload image to ComfyUI and return the server-side filename. | [src](../../../scripts/pipelines/jarvis_svd_pipeline.py#L130) |
| function | `_submit_workflow` | `(workflow, comfy_url=…)` | Submit workflow to ComfyUI queue and return prompt_id. | [src](../../../scripts/pipelines/jarvis_svd_pipeline.py#L143) |
| function | `_wait_for_completion` | `(prompt_id, comfy_url=…, timeout=…, poll_interval=…)` | Poll /history until the prompt completes. Returns outputs dict. | [src](../../../scripts/pipelines/jarvis_svd_pipeline.py#L152) |
| function | `_find_output_video` | `(outputs, comfy_url=…)` | Find video file path from ComfyUI outputs dict. | [src](../../../scripts/pipelines/jarvis_svd_pipeline.py#L175) |
| function | `_download_video` | `(filename, subfolder, dest_path, comfy_url=…)` | Download generated video from ComfyUI output dir or via API. | [src](../../../scripts/pipelines/jarvis_svd_pipeline.py#L187) |
| function | `generate_svd_video` | `(image_path, output_path=…, width=…, height=…, frames=…, fps=…, motion=…, steps=…, comfy_url=…)` | Generate an animated video from an image using SVD via ComfyUI. | [src](../../../scripts/pipelines/jarvis_svd_pipeline.py#L217) |

## `scripts/pipelines/jarvis_tiktok_pipeline.py`
_Jarvis TikTok Video Pipeline_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `create_zoom_video` | `(image_path, duration=…, zoom_start=…, zoom_end=…, fps=…, output_path=…)` | Create a satisfying slow-zoom video from an image. | [src](../../../scripts/pipelines/jarvis_tiktok_pipeline.py#L24) |
| function | `add_text_overlay` | `(image_path, text, font_size=…, color=…, output_path=…)` | Add centered text overlay to an image. | [src](../../../scripts/pipelines/jarvis_tiktok_pipeline.py#L54) |
| function | `create_quote_video` | `(image_path, quote, duration=…, zoom_start=…, zoom_end=…, fps=…, output_path=…)` | Create a satisfying zoom video with a motivational quote overlay. | [src](../../../scripts/pipelines/jarvis_tiktok_pipeline.py#L145) |

## `scripts/pipelines/tiktok_analytics.py`
_TikTok analytics — video-statistik for en given bruger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `fetch_profile` | `()` | Hent profil-data + secUid + userId via UNIVERSAL_DATA. | [src](../../../scripts/pipelines/tiktok_analytics.py#L53) |
| function | `_load_saved_cookies` | `()` | Load sessionid m.fl. fra TikTok uploader cookie-fil (JSON eller pickle). | [src](../../../scripts/pipelines/tiktok_analytics.py#L84) |
| function | `_cookies_to_header` | `(cookie_dict)` | — | [src](../../../scripts/pipelines/tiktok_analytics.py#L102) |
| function | `_get_tiktok_cookies` | `(extra_cookies)` | Kør headless Playwright, besøg TikTok, returner session-cookies. | [src](../../../scripts/pipelines/tiktok_analytics.py#L111) |
| function | `_fetch_video_list` | `(sec_uid, cookies, count=…)` | Hent video-liste via TikTok's interne API. | [src](../../../scripts/pipelines/tiktok_analytics.py#L150) |
| function | `run` | `(manual_ms_token, max_videos)` | — | [src](../../../scripts/pipelines/tiktok_analytics.py#L181) |
| function | `main` | `()` | — | [src](../../../scripts/pipelines/tiktok_analytics.py#L246) |

## `scripts/pipelines/tiktok_import_firefox_cookies.py`
_Import TikTok cookies from Firefox profile → TK_cookies_{account}.json_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `find_firefox_cookie_db` | `()` | — | [src](../../../scripts/pipelines/tiktok_import_firefox_cookies.py#L28) |
| function | `extract_tiktok_cookies` | `(db_path)` | — | [src](../../../scripts/pipelines/tiktok_import_firefox_cookies.py#L39) |
| function | `main` | `()` | — | [src](../../../scripts/pipelines/tiktok_import_firefox_cookies.py#L70) |

