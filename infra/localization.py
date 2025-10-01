# -*- coding: utf-8 -*-
"""Localization helpers with runtime language switching."""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict

from infra import settings as settings_module

LANGUAGE_NAMES: Dict[str, str] = {
    "ru": "\u0420\u0443\u0441\u0441\u043a\u0438\u0439",
    "en": "English",
}

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ru": {
    "window.title": "\u0056\u0065\u0063\u0074\u006f\u0072\u0020\u0053\u0074\u006f\u0072\u0065\u0020\u0055\u0070\u006c\u006f\u0061\u0064\u0065\u0072",
    "status.ready": "\u0413\u043e\u0442\u043e\u0432\u043e",
    "status.ready_with_id": "\u0413\u043e\u0442\u043e\u0432\u043e\u002e\u0020\u0053\u0074\u006f\u0072\u0065\u0020\u0049\u0044\u003a\u0020\u007b\u0073\u0074\u006f\u0072\u0065\u005f\u0069\u0064\u007d",
    "status.uploading": "\u0417\u0430\u0433\u0440\u0443\u0436\u0430\u044e\u0020\u0444\u0430\u0439\u043b\u044b\u2026",
    "status.processing": "\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430\u0020\u043f\u043e\u0020\u0441\u0438\u0441\u0442\u0435\u043c\u043d\u043e\u043c\u0443\u0020\u043f\u0440\u043e\u043c\u043f\u0442\u0443\u2026",
    "status.processing_done": "\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430\u0020\u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430\u002e",
    "status.processing_error": "\u041e\u0448\u0438\u0431\u043a\u0430\u0020\u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438\u002e",
    "status.validation_error": "\u041e\u0448\u0438\u0431\u043a\u0430\u003a\u0020\u004a\u0053\u004f\u004e\u0020\u043d\u0435\u0020\u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0443\u0435\u0442\u0020\u0441\u0445\u0435\u043c\u0435\u002e",
    "status.error": "\u041e\u0448\u0438\u0431\u043a\u0430\u002e",
    "dialog.select_files.title": "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435\u0020\u0444\u0430\u0439\u043b\u044b",
    "dialog.select_files.documents": "\u0414\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u044b",
    "dialog.select_files.all_files": "\u0412\u0441\u0435\u0020\u0444\u0430\u0439\u043b\u044b",
    "dialog.no_files.title": "\u041d\u0435\u0442\u0020\u0444\u0430\u0439\u043b\u043e\u0432",
    "dialog.no_files.message": "\u0421\u043d\u0430\u0447\u0430\u043b\u0430\u0020\u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435\u0020\u0444\u0430\u0439\u043b\u044b\u002e",
    "dialog.error.title": "\u041e\u0448\u0438\u0431\u043a\u0430",
    "dialog.no_store_id.message": "\u0421\u043d\u0430\u0447\u0430\u043b\u0430\u0020\u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u0435\u0020\u0444\u0430\u0439\u043b\u044b\u0020\u0438\u0020\u043f\u043e\u043b\u0443\u0447\u0438\u0442\u0435\u0020\u0053\u0074\u006f\u0072\u0065\u0020\u0049\u0044\u002e",
    "dialog.validation_error.title": "\u0412\u0430\u043b\u0438\u0434\u0430\u0446\u0438\u044f\u0020\u004a\u0053\u004f\u004e",
    "dialog.validation_error.message": "\u004a\u0053\u004f\u004e\u0020\u043d\u0435\u0020\u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0443\u0435\u0442\u0020\u0441\u0445\u0435\u043c\u0435\u002e\u0020\u041f\u043e\u0434\u0440\u043e\u0431\u043d\u043e\u0441\u0442\u0438\u0020\u2014\u0020\u0432\u0020\u043b\u043e\u0433\u0430\u0445\u0020\u043e\u043a\u043d\u0430\u002e",
    "dialog.processing_error.title": "\u041e\u0448\u0438\u0431\u043a\u0430\u0020\u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438",
    "dialog.journal.title": "\u0416\u0443\u0440\u043d\u0430\u043b",
    "dialog.journal.error_title": "\u0416\u0443\u0440\u043d\u0430\u043b",
    "dialog.journal.missing": "\u041c\u043e\u0434\u0443\u043b\u044c\u0020\u006c\u006f\u0067\u005f\u006a\u006f\u0075\u0072\u006e\u0061\u006c\u002e\u0070\u0079\u0020\u043d\u0435\u0020\u043d\u0430\u0439\u0434\u0435\u043d\u002e",
    "dialog.settings.title": "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438",
    "dialog.invalid_delay.title": "\u041d\u0435\u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u043e\u0435\u0020\u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435",
    "dialog.invalid_delay.message": "\u0412\u0432\u0435\u0434\u0438\u0442\u0435\u0020\u043f\u043e\u043b\u043e\u0436\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0435\u0020\u043a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e\u0020\u043c\u0438\u043d\u0443\u0442\u0020\u043d\u0435\u0020\u043c\u0435\u043d\u044c\u0448\u0435\u0020\u007b\u006d\u0069\u006e\u0069\u006d\u0075\u006d\u007d\u002e",
    "journal.window_title": "\u0416\u0443\u0440\u043d\u0430\u043b\u0020\u0437\u0430\u0433\u0440\u0443\u0437\u043e\u043a",
    "journal.empty": "\u041f\u043e\u043a\u0430\u0020\u0437\u0430\u043f\u0438\u0441\u0435\u0439\u0020\u043d\u0435\u0442\u002e\u000a",
    "log.files_selected": "\u0412\u044b\u0431\u0440\u0430\u043d\u044b\u0020\u0444\u0430\u0439\u043b\u044b\u003a",
    "log.files_selected_item": "\u0020\u2022\u0020\u007b\u0066\u0069\u006c\u0065\u006e\u0061\u006d\u0065\u007d",
    "log.upload_start": "\u000a\u2014\u0020\u041d\u0430\u0447\u0438\u043d\u0430\u044e\u0020\u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0443\u2026",
    "log.upload_result_header": "\u000a\u003d\u003d\u003d\u0020\u0420\u0415\u0417\u0423\u041b\u042c\u0422\u0410\u0422\u0020\u0417\u0410\u0413\u0420\u0423\u0417\u041a\u0418\u0020\u003d\u003d\u003d",
    "log.upload_complete": "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430\u0020\u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430\u002e",
    "log.cleanup_scheduled": "\U0001f5d3\u0020\u0410\u0432\u0442\u043e\u0443\u0434\u0430\u043b\u0435\u043d\u0438\u0435\u0020\u0437\u0430\u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u043e\u0020\u0447\u0435\u0440\u0435\u0437\u0020\u007b\u006d\u0069\u006e\u0075\u0074\u0065\u0073\u007d\u0020\u043c\u0438\u043d\u002e",
    "log.cleanup_failed": "\u26a0\u0020\u041d\u0435\u0020\u0443\u0434\u0430\u043b\u043e\u0441\u044c\u0020\u0437\u0430\u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u0442\u044c\u0020\u0430\u0432\u0442\u043e\u0443\u0434\u0430\u043b\u0435\u043d\u0438\u0435\u003a\u0020\u007b\u0065\u0072\u0072\u006f\u0072\u007d",
    "log.cleanup_done": "\U0001f5d1\u0020\u0425\u0440\u0430\u043d\u0438\u043b\u0438\u0449\u0435\u0020\u0443\u0434\u0430\u043b\u0435\u043d\u043e\u0020\u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u003a\u0020\u007b\u0073\u0074\u006f\u0072\u0065\u005f\u0069\u0064\u007d",
    "log.cleanup_error": "\u26a0\u0020\u0410\u0432\u0442\u043e\u0443\u0434\u0430\u043b\u0435\u043d\u0438\u0435\u0020\u0437\u0430\u0432\u0435\u0440\u0448\u0438\u043b\u043e\u0441\u044c\u0020\u0441\u0020\u043e\u0448\u0438\u0431\u043a\u043e\u0439\u0020\u0028\u007b\u0073\u0074\u006f\u0072\u0065\u005f\u0069\u0064\u007d\u0029\u003a\u0020\u007b\u0065\u0072\u0072\u006f\u0072\u007d",
    "log.processing_start": "\u000a\u2014\u0020\u0417\u0430\u043f\u0443\u0441\u043a\u0430\u044e\u0020\u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0443\u0020\u043f\u043e\u0020\u0441\u0438\u0441\u0442\u0435\u043c\u043d\u043e\u043c\u0443\u0020\u043f\u0440\u043e\u043c\u043f\u0442\u0443\u2026",
    "log.processing_done": "\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430\u0020\u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430\u002e",
    "log.extraction_header": "\u000a\u003d\u003d\u003d\u0020\u0420\u0415\u0417\u0423\u041b\u042c\u0422\u0410\u0422\u0020\u0418\u0417\u0412\u041b\u0415\u0427\u0415\u041d\u0418\u042f\u0020\u0028\u004a\u0053\u004f\u004e\u002c\u0020\u0432\u0430\u043b\u0438\u0434\u0430\u0446\u0438\u044f\u0020\u0050\u0079\u0064\u0061\u006e\u0074\u0069\u0063\u0029\u0020\u003d\u003d\u003d",
    "log.extraction_footer": "\u003d\u003d\u003d\u0020\u041a\u041e\u041d\u0415\u0426\u0020\u0420\u0415\u0417\u0423\u041b\u042c\u0422\u0410\u0422\u0410\u0020\u003d\u003d\u003d\u000a",
    "log.validation_error": "\u000a\u274c\u0020\u041e\u0448\u0438\u0431\u043a\u0430\u0020\u0432\u0430\u043b\u0438\u0434\u0430\u0446\u0438\u0438\u0020\u004a\u0053\u004f\u004e\u0020\u043f\u043e\u0020\u0441\u0445\u0435\u043c\u0435\u0020\u0438\u0437\u0020\u0073\u0079\u0073\u0074\u0065\u006d\u002e\u0070\u0072\u006f\u006d\u0070\u0074\u002e",
    "log.saved_copy": "\U0001f4be\u0020\u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0430\u0020\u043a\u043e\u043f\u0438\u044f\u0020\u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u0430\u003a\u0020\u007b\u0070\u0061\u0074\u0068\u007d",
    "log.save_copy_failed": "\u26a0\u0020\u041d\u0435\u0020\u0443\u0434\u0430\u043b\u043e\u0441\u044c\u0020\u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c\u0020\u043a\u043e\u043f\u0438\u044e\u0020\u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u0430\u003a\u0020\u007b\u0065\u0072\u0072\u006f\u0072\u007d",
    "log.invalid_delay": "\u26a0\u0020\u041d\u0435\u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u0430\u044f\u0020\u0437\u0430\u0434\u0435\u0440\u0436\u043a\u0430\u0020\u0430\u0432\u0442\u043e\u0443\u0434\u0430\u043b\u0435\u043d\u0438\u044f\u002c\u0020\u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u044e\u0020\u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435\u0020\u043f\u043e\u0020\u0443\u043c\u043e\u043b\u0447\u0430\u043d\u0438\u044e\u0020\u0028\u007b\u006d\u0069\u006e\u0075\u0074\u0065\u0073\u007d\u0020\u043c\u0438\u043d\u002e\u0029",
    "cli.description": "\u0043\u004c\u0049\u0020\u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0438\u0020\u0438\u0020\u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438\u0020\u0444\u0430\u0439\u043b\u043e\u0432\u0020\u0447\u0435\u0440\u0435\u0437\u0020\u0056\u0065\u0063\u0074\u006f\u0072\u0020\u0053\u0074\u006f\u0072\u0065",
    "cli.arg.files": "\u041f\u0443\u0442\u0438\u0020\u043a\u0020\u0444\u0430\u0439\u043b\u0430\u043c\u002e",
    "cli.arg.no_wait_index": "\u041d\u0435\u0020\u0436\u0434\u0430\u0442\u044c\u0020\u0438\u043d\u0434\u0435\u043a\u0441\u0430\u0446\u0438\u044e\u0020\u0028\u043f\u043e\u0020\u0443\u043c\u043e\u043b\u0447\u0430\u043d\u0438\u044e\u0020\u0436\u0434\u0451\u043c\u0029\u002e",
    "cli.arg.save_dir": "\u041f\u0430\u043f\u043a\u0430\u002c\u0020\u043a\u0443\u0434\u0430\u0020\u0434\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0020\u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c\u0020\u0437\u0430\u043f\u0438\u0441\u044c\u0020\u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u0430\u0020\u0028\u043a\u0430\u043a\u0020\u0432\u0020\u0436\u0443\u0440\u043d\u0430\u043b\u0435\u0029\u002e",
    "cli.arg.language": "\u041f\u0440\u0438\u043d\u0443\u0434\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0020\u0432\u044b\u0431\u0440\u0430\u0442\u044c\u0020\u044f\u0437\u044b\u043a\u0020\u0438\u043d\u0442\u0435\u0440\u0444\u0435\u0439\u0441\u0430\u002e",
    "cli.no_files": "\u0424\u0430\u0439\u043b\u044b\u0020\u043d\u0435\u0020\u0432\u044b\u0431\u0440\u0430\u043d\u044b\u002e\u0020\u0412\u044b\u0445\u043e\u0434\u002e",
    "cli.upload_error": "\u041e\u0448\u0438\u0431\u043a\u0430\u003a\u0020\u007b\u0065\u0072\u0072\u006f\u0072\u007d",
    "cli.wait_index_disabled": "\u26a0\u0020\u0418\u043d\u0434\u0435\u043a\u0441\u0430\u0446\u0438\u044f\u0020\u043e\u0442\u043a\u043b\u044e\u0447\u0435\u043d\u0430\u0020\u0028\u002d\u002d\u006e\u006f\u002d\u0077\u0061\u0069\u0074\u002d\u0069\u006e\u0064\u0065\u0078\u0029\u002e\u0020\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430\u0020\u043d\u0435\u0020\u0437\u0430\u043f\u0443\u0441\u043a\u0430\u0435\u0442\u0441\u044f\u002e",
    "cli.processing_start": "\u000a\u2014\u0020\u0417\u0430\u043f\u0443\u0441\u043a\u0430\u044e\u0020\u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0443\u0020\u043f\u043e\u0020\u0441\u0438\u0441\u0442\u0435\u043c\u043d\u043e\u043c\u0443\u0020\u043f\u0440\u043e\u043c\u043f\u0442\u0443\u2026",
    "cli.processing_error": "\u041e\u0448\u0438\u0431\u043a\u0430\u0020\u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438\u003a\u0020\u007b\u0065\u0072\u0072\u006f\u0072\u007d",
    "cli.saved_result": "\U0001f4be\u0020\u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u0020\u0442\u0430\u043a\u0436\u0435\u0020\u0441\u043e\u0445\u0440\u0430\u043d\u0451\u043d\u003a\u0020\u007b\u0070\u0061\u0074\u0068\u007d",
    "cli.language_set": "\u042f\u0437\u044b\u043a\u0020\u0043\u004c\u0049\u003a\u0020\u007b\u006c\u0061\u006e\u0067\u0075\u0061\u0067\u0065\u005f\u006e\u0061\u006d\u0065\u007d\u0020\u0028\u007b\u006c\u0061\u006e\u0067\u0075\u0061\u0067\u0065\u005f\u0063\u006f\u0064\u0065\u007d\u0029\u002e",
    "prompt.extract_instruction": "\u0418\u0437\u0432\u043b\u0435\u043a\u0438\u0020\u0434\u0430\u043d\u043d\u044b\u0435\u0020\u0441\u0442\u0440\u043e\u0433\u043e\u0020\u043f\u043e\u0020\u0441\u0438\u0441\u0442\u0435\u043c\u043d\u043e\u043c\u0443\u0020\u043f\u0440\u043e\u043c\u043f\u0442\u0443\u002e",
    "button.select_files": "\u0412\u044b\u0431\u0440\u0430\u0442\u044c\u0020\u0444\u0430\u0439\u043b\u044b",
    "button.upload": "\u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c",
    "button.process": "\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u0430\u0442\u044c",
    "button.journal": "\u0416\u0443\u0440\u043d\u0430\u043b",
    "button.settings": "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438",
    "checkbox.auto_delete": "\u0423\u0434\u0430\u043b\u0438\u0442\u044c\u0020\u043f\u043e\u0441\u043b\u0435\u0020\u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438",
    "label.delete_delay": "\u0417\u0430\u0434\u0435\u0440\u0436\u043a\u0430\u0020\u0028\u043c\u0438\u043d\u0029\u003a",
    "settings.title": "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438",
    "settings.language_label": "\u042f\u0437\u044b\u043a\u0020\u0438\u043d\u0442\u0435\u0440\u0444\u0435\u0439\u0441\u0430\u003a",
    "settings.close": "\u0417\u0430\u043a\u0440\u044b\u0442\u044c",
    "settings.language_hint": "\u0418\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u0435\u0020\u044f\u0437\u044b\u043a\u0430\u0020\u043f\u0440\u0438\u043c\u0435\u043d\u044f\u0435\u0442\u0441\u044f\u0020\u0441\u0440\u0430\u0437\u0443\u002e",
    "settings.language_applied": "\u042f\u0437\u044b\u043a\u0020\u043f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0435\u043d\u0020\u043d\u0430\u0020\u007b\u006c\u0061\u006e\u0067\u0075\u0061\u0067\u0065\u005f\u006e\u0061\u006d\u0065\u007d\u002e",
    "pipeline.missing_store_id": "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430\u0020\u0437\u0430\u0432\u0435\u0440\u0448\u0438\u043b\u0430\u0441\u044c\u0020\u0431\u0435\u0437\u0020\u0073\u0074\u006f\u0072\u0065\u005f\u0069\u0064\u002e",
},
    "en": {
    "button.journal": "Journal",
    "button.process": "Process",
    "button.select_files": "Select files",
    "button.settings": "Settings",
    "button.upload": "Upload",
    "checkbox.auto_delete": "Delete after processing",
    "cli.arg.files": "Paths to files.",
    "cli.arg.language": "Force the interface language.",
    "cli.arg.no_wait_index": "Do not wait for indexing (wait by default).",
    "cli.arg.save_dir": "Directory to additionally save the validated result record (same format as the journal).",
    "cli.description": "CLI for uploading and processing files via Vector Store",
    "cli.language_set": "CLI language: {language_name} ({language_code}).",
    "cli.no_files": "No files selected. Exiting.",
    "cli.processing_error": "Processing error: {error}",
    "cli.processing_start": "\n\u2014 Starting extraction with the system prompt\u2026",
    "cli.saved_result": "\U0001f4be Result also saved: {path}",
    "cli.upload_error": "Error: {error}",
    "cli.wait_index_disabled": "\u26a0 Indexing skipped (--no-wait-index). Extraction will not start.",
    "dialog.error.title": "Error",
    "dialog.invalid_delay.message": "Enter a positive number of minutes greater than or equal to {minimum}.",
    "dialog.invalid_delay.title": "Invalid value",
    "dialog.journal.error_title": "Journal",
    "dialog.journal.missing": "The log_journal.py module is not available.",
    "dialog.journal.title": "Journal",
    "dialog.no_files.message": "Please select files first.",
    "dialog.no_files.title": "No files",
    "dialog.no_store_id.message": "Upload files and obtain a Store ID first.",
    "dialog.processing_error.title": "Processing error",
    "dialog.select_files.all_files": "All files",
    "dialog.select_files.documents": "Documents",
    "dialog.select_files.title": "Select files",
    "dialog.settings.title": "Settings",
    "dialog.validation_error.message": "The JSON does not conform to the schema. Check the log window for details.",
    "dialog.validation_error.title": "JSON validation",
    "journal.empty": "No records yet.\n",
    "journal.window_title": "Upload journal",
    "label.delete_delay": "Delay (min):",
    "log.cleanup_done": "\U0001f5d1 Store removed automatically: {store_id}",
    "log.cleanup_error": "\u26a0 Auto deletion finished with an error ({store_id}): {error}",
    "log.cleanup_failed": "\u26a0 Failed to schedule auto deletion: {error}",
    "log.cleanup_scheduled": "\U0001f5d3 Auto deletion scheduled in {minutes} min.",
    "log.extraction_footer": "=== END OF RESULT ===\n",
    "log.extraction_header": "\n=== EXTRACTION RESULT (JSON, validated with Pydantic) ===",
    "log.files_selected": "Selected files:",
    "log.files_selected_item": " \u2022 {filename}",
    "log.invalid_delay": "\u26a0 Invalid auto deletion delay, using the default ({minutes} min).",
    "log.processing_done": "Extraction finished.",
    "log.processing_start": "\n\u2014 Starting extraction with the system prompt\u2026",
    "log.save_copy_failed": "\u26a0 Failed to save a copy of the result: {error}",
    "log.saved_copy": "\U0001f4be Saved a copy of the result: {path}",
    "log.upload_complete": "Upload finished.",
    "log.upload_result_header": "\n=== UPLOAD SUMMARY ===",
    "log.upload_start": "\n\u2014 Starting upload\u2026",
    "log.validation_error": "\n\u274c JSON validation error against the system.prompt schema.",
    "pipeline.missing_store_id": "Upload completed without a store_id.",
    "prompt.extract_instruction": "Extract the data strictly according to the system prompt.",
    "settings.close": "Close",
    "settings.language_applied": "Language switched to {language_name}.",
    "settings.language_hint": "Language changes apply immediately.",
    "settings.language_label": "Interface language:",
    "settings.title": "Settings",
    "status.error": "Error.",
    "status.processing": "Processing via system prompt\u2026",
    "status.processing_done": "Processing finished.",
    "status.processing_error": "Processing error.",
    "status.ready": "Ready",
    "status.ready_with_id": "Ready. Store ID: {store_id}",
    "status.uploading": "Uploading files\u2026",
    "status.validation_error": "Error: JSON does not match the schema.",
    "window.title": "Vector Store Uploader"
},
}

_DEFAULT_LANGUAGE = settings_module.DEFAULT_SETTINGS["language"]
_lock = threading.RLock()
_current_language: str | None = None
_listeners: list[Callable[[str], None]] = []


def _normalize_language(language: str | None) -> str:
    if not language:
        return _DEFAULT_LANGUAGE
    candidate = str(language).lower()
    if candidate in TRANSLATIONS:
        return candidate
    for code in TRANSLATIONS:
        if code.lower() == candidate:
            return code
    return _DEFAULT_LANGUAGE


def available_languages() -> tuple[str, ...]:
    return tuple(TRANSLATIONS.keys())


def language_name(language: str) -> str:
    return LANGUAGE_NAMES.get(language, language)


def get_language() -> str:
    global _current_language
    with _lock:
        if _current_language is None:
            _current_language = _normalize_language(settings_module.get_language(_DEFAULT_LANGUAGE))
        return _current_language


def set_language(language: str, persist: bool = True) -> str:
    normalized = _normalize_language(language)
    with _lock:
        global _current_language
        changed = _current_language != normalized
        if changed:
            _current_language = normalized
        listeners = tuple(_listeners)
    if persist:
        settings_module.set_language(normalized)
    if changed:
        for callback in listeners:
            try:
                callback(normalized)
            except Exception:
                pass
    return normalized


def translate(key: str, default: str | None = None, **kwargs: Any) -> str:
    language = get_language()
    text = TRANSLATIONS.get(language, {}).get(key)
    if text is None:
        text = TRANSLATIONS.get(_DEFAULT_LANGUAGE, {}).get(key, default if default is not None else key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


T = translate


def register_listener(callback: Callable[[str], None]) -> Callable[[], None]:
    with _lock:
        _listeners.append(callback)

    def _unsubscribe() -> None:
        unregister_listener(callback)

    return _unsubscribe


def unregister_listener(callback: Callable[[str], None]) -> None:
    with _lock:
        try:
            _listeners.remove(callback)
        except ValueError:
            pass


def reload_language_from_settings() -> str:
    return set_language(settings_module.get_language(_DEFAULT_LANGUAGE), persist=False)


__all__ = [
    "LANGUAGE_NAMES",
    "TRANSLATIONS",
    "available_languages",
    "language_name",
    "get_language",
    "set_language",
    "translate",
    "T",
    "register_listener",
    "unregister_listener",
    "reload_language_from_settings",
]


reload_language_from_settings()






