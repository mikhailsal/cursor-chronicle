#!/usr/bin/env python3
"""
Cursor Chat Viewer
Извлекает и отображает диалоги из базы данных Cursor IDE с поддержкой 
прикрепленных файлов.
"""

import sqlite3
import json
import os
import argparse
import signal
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import urllib.parse
import base64

# Handle broken pipe gracefully
signal.signal(signal.SIGPIPE, signal.SIG_DFL)


class CursorChatViewer:
    def __init__(self):
        self.cursor_config_path = Path.home() / ".config" / "Cursor" / "User"
        self.workspace_storage_path = (
            self.cursor_config_path / "workspaceStorage"
        )
        self.global_storage_path = (
            self.cursor_config_path / "globalStorage" / "state.vscdb"
        )
        
        # Tool type mapping
        self.tool_types = {
            1: "🔍 Codebase Search",
            3: "🔎 Grep Search", 
            5: "📖 Read File",
            6: "📁 List Directory",
            7: "✏️ Edit File",
            8: "🔍 File Search",
            9: "🔍 Codebase Search",
            11: "🗑️ Delete File",
            12: "🔄 Reapply",
            15: "⚡ Terminal Command",
            16: "📋 Fetch Rules",
            18: "🌐 Web Search",
            19: "🔧 MCP Tool"
        }
    
    def get_projects(self) -> List[Dict]:
        """Получить список всех проектов с их метаданными"""
        projects = []
        
        for workspace_dir in self.workspace_storage_path.iterdir():
            if not workspace_dir.is_dir():
                continue
                
            workspace_json = workspace_dir / "workspace.json"
            state_db = workspace_dir / "state.vscdb"
            
            if not workspace_json.exists() or not state_db.exists():
                continue
            
            try:
                # Читаем информацию о проекте
                with open(workspace_json, 'r') as f:
                    workspace_data = json.load(f)
                
                folder_uri = workspace_data.get('folder', '')
                if folder_uri.startswith('file://'):
                    folder_path = urllib.parse.unquote(folder_uri[7:])
                    project_name = os.path.basename(folder_path)
                else:
                    project_name = folder_uri
                
                # Читаем данные композеров из базы
                conn = sqlite3.connect(state_db)
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT value FROM ItemTable WHERE key = "
                    "'composer.composerData'"
                )
                result = cursor.fetchone()
                
                if result:
                    composer_data = json.loads(result[0])
                    composers = composer_data.get('allComposers', [])
                    
                    # Находим самый свежий диалог
                    latest_dialog = None
                    if composers:
                        latest_dialog = max(
                            composers, key=lambda x: x.get('lastUpdatedAt', 0)
                        )
                    
                    projects.append({
                        'workspace_id': workspace_dir.name,
                        'project_name': project_name,
                        'folder_path': (
                            folder_path if folder_uri.startswith('file://')
                            else folder_uri
                        ),
                        'composers': composers,
                        'latest_dialog': latest_dialog,
                        'state_db_path': str(state_db)
                    })
                
                conn.close()
                
            except Exception:
                print(f"Ошибка при обработке проекта {workspace_dir.name}")
                continue
        
        # Сортируем проекты по времени последнего диалога
        projects.sort(
            key=lambda x: x['latest_dialog'].get('lastUpdatedAt', 0)
            if x['latest_dialog']
            else 0,
            reverse=True
        )
        return projects
    
    def get_dialog_messages(self, composer_id: str) -> List[Dict]:
        """Получить все сообщения диалога по ID композера"""
        if not self.global_storage_path.exists():
            raise FileNotFoundError(
                f"Глобальная база данных не найдена: "
                f"{self.global_storage_path}"
            )
        
        conn = sqlite3.connect(self.global_storage_path)
        cursor = conn.cursor()
        
        # Сначала получаем данные композера для правильного порядка
        cursor.execute(
            """SELECT value FROM cursorDiskKV 
            WHERE key = ? AND LENGTH(value) > 100""",
            (f'composerData:{composer_id}',)
        )
        
        composer_result = cursor.fetchone()
        ordered_bubble_ids = []
        
        if composer_result:
            try:
                composer_data = json.loads(composer_result[0])
                # Получаем правильный порядок из fullConversationHeadersOnly
                if 'fullConversationHeadersOnly' in composer_data:
                    ordered_bubble_ids = [
                        bubble['bubbleId']
                        for bubble in 
                        composer_data['fullConversationHeadersOnly']
                    ]
            except json.JSONDecodeError:
                pass
        
        # Если нет fullConversationHeadersOnly, используем старый метод
        if not ordered_bubble_ids:
            cursor.execute(
                """SELECT rowid, key, value FROM cursorDiskKV 
                WHERE key LIKE ? AND LENGTH(value) > 100 
                ORDER BY rowid""",
                (f'bubbleId:{composer_id}:%',)
            )
            results = cursor.fetchall()
        else:
            # Получаем пузырьки в правильном порядке
            results = []
            for bubble_id in ordered_bubble_ids:
                cursor.execute(
                    """SELECT rowid, key, value FROM cursorDiskKV 
                    WHERE key = ? AND LENGTH(value) > 100""",
                    (f'bubbleId:{composer_id}:{bubble_id}',)
                )
                result = cursor.fetchone()
                if result:
                    results.append(result)
        
        conn.close()
        
        messages = []
        for rowid, key, value in results:
            try:
                bubble_data = json.loads(value)
                text = bubble_data.get('text', '').strip()
                bubble_type = bubble_data.get('type')
                tool_data = bubble_data.get('toolFormerData')
                thinking_data = bubble_data.get('thinking')
                
                message = {
                    'text': text,
                    'type': bubble_type,
                    'bubble_id': bubble_data.get('bubbleId', ''),
                    'key': key,
                    'rowid': rowid,
                    'tool_data': tool_data,
                    'attached_files': self.extract_attached_files(bubble_data),
                    'is_thought': False,  # Default to False
                    'thinking_duration': 0,  # Default to 0
                    'thinking_content': '',  # Default to empty
                    'token_count': bubble_data.get('tokenCount', {}),
                    'usage_uuid': bubble_data.get('usageUuid'),
                    'server_bubble_id': bubble_data.get('serverBubbleId'),
                    'is_agentic': bubble_data.get('isAgentic', False),
                    'capabilities_ran': bubble_data.get('capabilitiesRan', {}),
                    'unified_mode': bubble_data.get('unifiedMode'),
                    'use_web': bubble_data.get('useWeb', False),
                    'is_refunded': bubble_data.get('isRefunded', False)
                }
                
                # Check for AI thinking bubbles - improved logic
                if bubble_type == 2 and not text:
                    # Check multiple possible fields for thinking indication
                    is_thought_bubble = (
                        bubble_data.get('isThought') or
                        bubble_data.get('thinking') or
                        bubble_data.get('thinkingDurationMs') or
                        thinking_data
                    )
                    if is_thought_bubble:
                        message['is_thought'] = True
                        message['thinking_duration'] = (
                            bubble_data.get('thinkingDurationMs', 0)
                        )
                        
                        # Extract thinking content from various possible fields
                        thinking_content = ''
                        if thinking_data:
                            if isinstance(thinking_data, dict):
                                # Try different fields that might contain 
                                # thinking content
                                thinking_content = (
                                    thinking_data.get('content') or
                                    thinking_data.get('text') or
                                    thinking_data.get('thinking') or
                                    thinking_data.get('signature') or
                                    ''
                                )
                                # If signature contains encoded content, 
                                # try to decode it
                                if (thinking_content and 
                                        thinking_content.startswith('AVSoXO')):
                                    # This appears to be base64 encoded 
                                    # thinking content
                                    try:
                                        # Try to decode the signature 
                                        # (it might be base64)
                                        decoded = base64.b64decode(
                                            thinking_content)
                                        # Check if it's readable text
                                        decoded_text = decoded.decode(
                                            'utf-8', errors='ignore')
                                        if decoded_text.isprintable():
                                            thinking_content = decoded_text
                                    except Exception:
                                        # If decoding fails, show a placeholder
                                        thinking_content = (
                                            '[Thinking content available '
                                            'but encoded]')
                                elif not thinking_content:
                                    # Fallback to string representation if 
                                    # no specific field found
                                    thinking_content = (
                                        str(thinking_data) 
                                        if thinking_data else '')
                            elif isinstance(thinking_data, str):
                                thinking_content = thinking_data
                        
                        # Also check for thinking content in the main bubble data
                        if not thinking_content:
                            thinking_content = (
                                bubble_data.get('thinkingContent') or
                                bubble_data.get('thinking_content') or
                                bubble_data.get('thoughtContent') or
                                ''
                            )
                        
                        message['thinking_content'] = thinking_content
                
                # Add messages with text, tool data, attached files, or thinking data
                if (text or tool_data or message['attached_files'] or
                        message['is_thought']):
                    messages.append(message)
                    
            except json.JSONDecodeError:
                continue
        
        return messages
    
    def extract_attached_files(self, bubble_data: Dict) -> List[Dict]:
        """Extract attached files from bubble data"""
        attached_files = []
        
        # 1. Активный файл (открытый в редакторе)
        current_file = bubble_data.get('currentFileLocationData')
        if current_file and isinstance(current_file, dict):
            # Пробуем разные поля для пути к файлу
            file_path = (
                current_file.get('relativeWorkspacePath') or
                current_file.get('filePath') or
                current_file.get('path', '')
            )
            line_number = current_file.get('lineNumber', 0)
            if file_path:
                attached_files.append({
                    'type': 'active',
                    'path': file_path,
                    'line': line_number,
                    'preview': (
                        current_file.get('text') or
                        current_file.get('filePreview', '')
                    )
                })
        
        # 2. Релевантные файлы из projectLayouts
        project_layouts = bubble_data.get('projectLayouts')
        if project_layouts:
            if isinstance(project_layouts, list):
                # Если это список JSON-строк
                for layout_str in project_layouts:
                    try:
                        layout_data = (
                            json.loads(layout_str)
                            if isinstance(layout_str, str)
                            else layout_str
                        )
                        relevant_files = self.extract_files_from_layout(
                            layout_data
                        )
                        for file_path in relevant_files:
                            attached_files.append({
                                'type': 'project',
                                'path': file_path
                            })
                    except (json.JSONDecodeError, TypeError):
                        continue
            else:
                # Если это объект
                relevant_files = self.extract_files_from_layout(project_layouts)
                for file_path in relevant_files:
                    attached_files.append({
                        'type': 'project',
                        'path': file_path
                    })
        
        # 3. Прикрепленные файлы из codebaseContextChunks (основной источник)
        codebase_chunks = bubble_data.get('codebaseContextChunks', [])
        if codebase_chunks:
            chunk_files = set()  # Используем set для избежания дублей
            for chunk_str in codebase_chunks:
                try:
                    if isinstance(chunk_str, str):
                        chunk = json.loads(chunk_str)
                        file_path = chunk.get('relativeWorkspacePath', '')
                        if file_path and file_path not in chunk_files:
                            chunk_files.add(file_path)
                            # Дополнительная информация о чанке
                            range_info = chunk.get('range', {})
                            start_pos = range_info.get('startPosition', {})
                            end_pos = range_info.get('endPosition', {})
                            
                            attached_files.append({
                                'type': 'context',
                                'path': file_path,
                                'start_line': start_pos.get('line', 0),
                                'end_line': end_pos.get('line', 0),
                                'content_preview': (
                                    chunk.get('contents', '')[:100] + '...' 
                                    if chunk.get('contents')
                                    else ''
                                )
                            })
                except (json.JSONDecodeError, TypeError):
                    continue
        
        # 4. Выбранные файлы (если есть отдельное поле)
        selected_files = bubble_data.get('attachedFileCodeChunksUris', [])
        if selected_files:
            for file_uri in selected_files:
                # Если это dict с path, извлекаем путь
                if isinstance(file_uri, dict):
                    path = file_uri.get('path', str(file_uri))
                else:
                    path = str(file_uri)
                
                attached_files.append({
                    'type': 'selected',
                    'path': path
                })
        
        # 5. Релевантные файлы из отдельного поля
        relevant_files = bubble_data.get('relevantFiles', [])
        for file_path in relevant_files:
            if isinstance(file_path, str):
                attached_files.append({
                    'type': 'relevant',
                    'path': file_path
                })
        
        # 6. Файлы из context.fileSelections
        context = bubble_data.get('context', {})
        if context:
            file_selections = context.get('fileSelections', [])
            for file_sel in file_selections:
                if isinstance(file_sel, dict) and file_sel.get('path'):
                    attached_files.append({
                        'type': 'context_selected',
                        'path': file_sel.get('path'),
                        'selection': file_sel.get('selection')
                    })
        
        return attached_files
    
    def extract_files_from_layout(self, layout_data: Dict, 
                                  current_path: str = "") -> List[str]:
        """Рекурсивно извлечь все пути файлов из структуры проекта"""
        files = []
        
        content = layout_data.get('content', {})
        if not content:
            return files
        
        # Обрабатываем файлы в текущей директории
        for file_info in content.get('files', []):
            if isinstance(file_info, dict) and file_info.get('name'):
                file_path = (
                    os.path.join(current_path, file_info['name'])
                    if current_path
                    else file_info['name']
                )
                files.append(file_path)
        
        # Рекурсивно обрабатываем поддиректории
        for dir_info in content.get('directories', []):
            if isinstance(dir_info, dict) and dir_info.get('name'):
                dir_path = (
                    os.path.join(current_path, dir_info['name'])
                    if current_path
                    else dir_info['name']
                )
                files.extend(self.extract_files_from_layout(dir_info, dir_path))
        
        return files
    
    def format_attached_files(self, attached_files: List[Dict], 
                              max_output_lines: int) -> str:
        """Format attached files for display"""
        if not attached_files:
            return ""
        
        # Группируем файлы по типам
        files_by_type = {}
        for file_info in attached_files:
            file_type = file_info.get('type', 'unknown')
            if file_type not in files_by_type:
                files_by_type[file_type] = []
            files_by_type[file_type].append(file_info)
        
        result = []
        
        # Активный файл
        if 'active' in files_by_type:
            result.append("📍 **Активный файл:**")
            for file_info in files_by_type['active']:
                line_info = (f" (строка {file_info['line']})"
                             if file_info.get('line') else "")
                result.append(f"   `{file_info['path']}`{line_info}")
                if file_info.get('preview'):
                    # Apply truncation for active file preview
                    preview_lines = file_info['preview'].splitlines()
                    if len(preview_lines) > max_output_lines:
                        preview = (
                            "\n".join(preview_lines[:max_output_lines]) +
                            f"... ({len(preview_lines) - max_output_lines} more lines)"
                        )
                    else:
                        preview = file_info['preview']
                    result.append(f"   💬 {preview}")
        
        # Выбранные файлы (явно прикрепленные пользователем)
        if 'selected' in files_by_type:
            result.append("✅ **Выбранные файлы:**")
            for file_info in files_by_type['selected']:
                result.append(f"   `{file_info['path']}`")
        
        # Файлы из контекста кодовой базы
        if 'context' in files_by_type:
            result.append("📎 **Контекстные файлы:**")
            for file_info in files_by_type['context']:
                path = file_info['path']
                start_line = file_info.get('start_line', 0)
                end_line = file_info.get('end_line', 0)
                
                if start_line and end_line:
                    line_info = f" (строки {start_line}-{end_line})"
                else:
                    line_info = ""
                
                result.append(f"   `{path}`{line_info}")
                
                # Показываем превью содержимого если есть
                if file_info.get('content_preview'):
                    # Apply truncation for context file preview
                    preview_lines = file_info['content_preview'].splitlines()
                    if len(preview_lines) > max_output_lines:
                        preview = (
                            "\n".join(preview_lines[:max_output_lines]) +
                            f"... ({len(preview_lines) - max_output_lines} more lines)"
                        )
                    else:
                        preview = file_info['content_preview']
                    if preview:
                        result.append(f"   💬 {preview}")
        
        # Релевантные файлы
        if 'relevant' in files_by_type:
            result.append("🔗 **Релевантные файлы:**")
            for file_info in files_by_type['relevant']:
                result.append(f"   `{file_info['path']}`")
        
        # Файлы из структуры проекта
        if 'project' in files_by_type:
            project_files = files_by_type['project']
            result.append(
                f"📁 **Файлы проекта** ({len(project_files)} файлов):"
            )
            # Показываем только первые 10 файлов, чтобы не загромождать вывод
            for file_info in project_files[:10]:
                result.append(f"   `{file_info['path']}`")
            if len(project_files) > 10:
                result.append(f"   ... и еще {len(project_files) - 10} файлов")
        
        # Выбранные файлы из контекста
        if 'context_selected' in files_by_type:
            result.append("🎯 **Выбранные в контексте:**")
            for file_info in files_by_type['context_selected']:
                result.append(f"   `{file_info['path']}`")
                if file_info.get('selection'):
                    result.append(f"   📄 Выделение: {file_info['selection']}")
        
        return "\n".join(result)
    
    def format_tool_call(self, tool_data: Dict, max_output_lines: int = 1) -> str:
        """Форматировать вызов инструмента"""
        if not tool_data or (
            tool_data.get('tool') is None and not tool_data.get('name')
        ):
            return ""
        
        tool_type = tool_data.get('tool')
        tool_name = tool_data.get('name', 'unknown')
        status = tool_data.get('status', 'unknown')
        user_decision = tool_data.get('userDecision', 'unknown')
        
        # Получаем иконку для типа инструмента
        tool_icon = "🔧 Unknown Tool"
        if isinstance(tool_type, int) and tool_type in self.tool_types:
            tool_icon = self.tool_types[tool_type]
        elif isinstance(tool_type, int):
            tool_icon = f"🔧 Tool {tool_type}"
        
        output = []
        output.append(f"🛠️ ИНСТРУМЕНТ: {tool_icon}")
        output.append(f"   Название: {tool_name}")
        output.append(f"   Статус: {status}")
        
        if user_decision != 'unknown':
            decision_icon = "✅" if user_decision == "accepted" else "❌"
            output.append(f"   Решение: {decision_icon} {user_decision}")
        
        # Показываем параметры если есть
        raw_args = tool_data.get('rawArgs')
        if raw_args:
            try:
                args = json.loads(raw_args)
                output.append("   Параметры:")
                for key, value in args.items():
                    if isinstance(value, str) and key == 'explanation':
                        pass  # Do not truncate explanation
                    elif (
                        tool_name in ['edit_file', 'search_replace'] and
                        key == 'code_edit'
                    ):
                        # Apply truncation for code_edit in edit_file
                        value_lines = value.splitlines()
                        if len(value_lines) > max_output_lines:
                            value = (
                                "\n".join(value_lines[:max_output_lines]) +
                                f"... ({len(value_lines) - max_output_lines} more lines)"
                            )
                        output.append(f"     {key}: {value}")
                        continue  # Skip general truncation for code_edit
                    elif isinstance(value, str) and len(value) > 70:  # general params
                        value = value[:70] + "..."
                    output.append(f"     {key}: {value}")
            except json.JSONDecodeError:
                pass
        
        # Показываем результат если есть
        result = tool_data.get('result')
        if result:
            try:
                result_data = json.loads(result)
                output.append("   Результат:")
                
                # Специальная обработка для чтения файлов
                if tool_name == 'read_file':
                    for key, value in result_data.items():
                        if key == 'contents':
                            # Apply truncation only to 'contents'
                            value_lines = str(value).splitlines()
                            if len(value_lines) > max_output_lines:
                                value_str = (
                                    "\n".join(value_lines[:max_output_lines]) +
                                    f"... ({len(value_lines) - max_output_lines} more lines)"
                                )
                            else:
                                value_str = str(value)
                            output.append(f"     {key}: {value_str}")
                        else:
                            # Display other fields without truncation
                            output.append(f"     {key}: {value}")
                
                # Специальная обработка для терминальных команд
                elif tool_name == 'run_terminal_cmd':
                    cmd_output = result_data.get('output', '')
                    exit_code = result_data.get('exitCodeV2', 'unknown')
                    output.append(f"     Код выхода: {exit_code}")
                    if cmd_output:
                        # Apply truncation for command output
                        lines = cmd_output.splitlines()
                        if len(lines) > max_output_lines:
                            cmd_output = (
                                "\n".join(lines[:max_output_lines]) +
                                f"... ({len(lines) - max_output_lines} more lines)"
                            )
                        output.append(f"     Вывод: {cmd_output}")
                
                # Специальная обработка для редактирования файлов
                elif tool_name in ['edit_file', 'search_replace']:
                    if 'diff' in result_data:
                        diff_data = result_data['diff']
                        if 'chunks' in diff_data:
                            output.append("     Изменения:")
                            total_lines_added = sum(
                                chunk.get('linesAdded', 0)
                                for chunk in diff_data['chunks']
                            )
                            total_lines_removed = sum(
                                chunk.get('linesRemoved', 0)
                                for chunk in diff_data['chunks']
                            )
                            
                            if max_output_lines == 1:
                                output.append(
                                    f"       +{total_lines_added} -{total_lines_removed} "
                                    "строк (детали скрыты)"
                                )
                            else:
                                # Show detailed diff chunks up to max_output_lines
                                lines_shown = 0
                                for chunk in diff_data['chunks']:
                                    if lines_shown >= max_output_lines: 
                                        break
                                    diff_string = chunk.get('diffString', '')
                                    chunk_lines = diff_string.splitlines()
                                    lines_to_show = min(
                                        len(chunk_lines), max_output_lines - lines_shown
                                    )
                                    
                                    for line in chunk_lines[:lines_to_show]:
                                        output.append(f"       {line}")
                                    lines_shown += lines_to_show
                                    
                                    if len(chunk_lines) > lines_to_show:  # more lines
                                        output.append(
                                            f"       ... ({len(chunk_lines) - lines_to_show} "
                                            "more lines in chunk)"
                                        )
                                
                                if (
                                    total_lines_added + total_lines_removed > lines_shown
                                ):  # Indicate total more lines
                                    output.append(
                                        f"       ... (Total changes: +{total_lines_added} "
                                        f"-{total_lines_removed} строк)"
                                    )
                
                # Для других инструментов показываем краткую информацию
                else:
                    # Apply truncation for other results
                    if isinstance(result_data, dict):
                        items = list(result_data.items())
                        if len(items) > max_output_lines:
                            output.append(
                                f"     (Показано {max_output_lines} из {len(items)} полей)"
                            )
                            items = items[:max_output_lines]
                        for key, value in items:
                            value_str = str(value)
                            if len(value_str) > 70:  # Reduce character limit
                                value_str = value_str[:70] + "..."
                            output.append(f"     {key}: {value_str}")
                    else:
                        result_str = str(result_data)
                        lines = result_str.splitlines()
                        if len(lines) > max_output_lines:
                            result_str = (
                                "\n".join(lines[:max_output_lines]) +
                                f"... ({len(lines) - max_output_lines} more lines)"
                            )
                        output.append(f"     {result_str}")
                        
            except json.JSONDecodeError:
                pass
        
        return "\n".join(output)
    
    def format_token_info(self, message: Dict) -> str:
        """Format token usage and metadata information for a message"""
        token_count = message.get('token_count', {})
        usage_uuid = message.get('usage_uuid')
        server_bubble_id = message.get('server_bubble_id')
        is_agentic = message.get('is_agentic', False)
        capabilities_ran = message.get('capabilities_ran', {})
        unified_mode = message.get('unified_mode')
        use_web = message.get('use_web', False)
        is_refunded = message.get('is_refunded', False)
        
        if not any([token_count, usage_uuid, server_bubble_id, is_agentic, 
                    capabilities_ran, unified_mode, use_web, is_refunded]):
            return ""
        
        output = []
        
        # Token information and model inference
        if token_count:
            input_tokens = token_count.get('inputTokens', 0)
            output_tokens = token_count.get('outputTokens', 0)
            total_tokens = input_tokens + output_tokens
            
            if total_tokens > 0:
                output.append(
                    f"🪙 ТОКЕНЫ: {total_tokens} "
                    f"(вход: {input_tokens}, выход: {output_tokens})"
                )
                
                # Try to infer model from token patterns or context
                # model_hint = self.infer_model_from_context(message, total_tokens)
                # if model_hint:
                #     output.append(f"🤖 МОДЕЛЬ: {model_hint}")
                # else:
                #     output.append("🤖 МОДЕЛЬ: Не указана в БД")
        
        # Usage UUID (for tracking)
        # if usage_uuid:
        #     output.append(f"🆔 Usage ID: {usage_uuid}")
        
        # Server bubble ID (for debugging)
        # if server_bubble_id:
        #     output.append(f"🔗 Server ID: {server_bubble_id}")
        
        # Agentic mode indicator
        if is_agentic:
            output.append("🤖 РЕЖИМ: Агентский")
        
        # Web usage indicator
        if use_web:
            output.append("🌐 ИСПОЛЬЗУЕТ: Веб-поиск")
        
        # Unified mode indicator
        if unified_mode is not None:
            output.append(f"🔧 РЕЖИМ: Unified {unified_mode}")
        
        # Refund status
        if is_refunded:
            output.append("💸 СТАТУС: Возвращен")
        
        # Capabilities that ran (if any significant ones)
        if capabilities_ran:
            significant_caps = []
            for cap_name, cap_list in capabilities_ran.items():
                if cap_list:  # Non-empty list
                    significant_caps.append(f"{cap_name}({len(cap_list)})")
            
            if significant_caps:
                output.append(
                    f"⚙️ ВОЗМОЖНОСТИ: {', '.join(significant_caps)}"
                )
        
        return "\n".join(output)
    
    def infer_model_from_context(self, message: Dict, total_tokens: int) -> str:
        """Try to infer the model used based on available context"""
        # Check if this is an agentic message (might indicate specific models)
        if message.get('is_agentic', False):
            return "Вероятно Claude (агентский режим)"
        
        # Check capabilities for hints about model type
        capabilities_ran = message.get('capabilities_ran', {})
        if capabilities_ran:
            # If there are many capabilities, it might be a more advanced model
            active_caps = [cap for cap, data in capabilities_ran.items() 
                          if data]
            if len(active_caps) > 5:
                return "Вероятно продвинутая модель"
        
        # Check token patterns (rough heuristics)
        if total_tokens > 10000:
            return "Большая модель (много токенов)"
        elif total_tokens > 1000:
            return "Средняя модель"
        
        # Check message content for model hints
        text = message.get('text', '')
        if text:
            text_lower = text.lower()
            if any(hint in text_lower for hint in 
                   ['claude', 'sonnet', 'haiku']):
                return "Claude (упомянут в тексте)"
            elif any(hint in text_lower for hint in 
                     ['gpt', 'openai']):
                return "GPT (упомянут в тексте)"
        
        return ""
    
    def format_dialog(self, messages: List[Dict], dialog_name: str, 
                      project_name: str, max_output_lines: int) -> str:
        """Форматировать диалог для отображения"""
        output = []
        output.append("=" * 60)
        output.append(f"ПРОЕКТ: {project_name}")
        output.append(f"ДИАЛОГ: {dialog_name}")
        output.append("=" * 60)
        output.append("")
        
        # Token counters for summary
        total_input_tokens = 0
        total_output_tokens = 0
        messages_with_tokens = 0
        
        for msg in messages:
            msg_type = msg['type']
            text = msg['text']
            tool_data = msg.get('tool_data')
            attached_files = msg.get('attached_files', [])
            is_thought = msg.get('is_thought', False)
            thinking_duration = msg.get('thinking_duration', 0)
            
            # Count tokens
            token_count = msg.get('token_count', {})
            if token_count:
                input_tokens = token_count.get('inputTokens', 0)
                output_tokens = token_count.get('outputTokens', 0)
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
                if input_tokens > 0 or output_tokens > 0:
                    messages_with_tokens += 1
            
            # Показываем пользовательские сообщения
            if msg_type == 1 and text:
                output.append("👤 ПОЛЬЗОВАТЕЛЬ:")
                output.append(text)
                
                # Token info for user messages
                token_info = self.format_token_info(msg)
                if token_info:
                    output.append("")
                    output.append(token_info)
                
                # Показываем прикрепленные файлы для пользовательских сообщений
                if attached_files:
                    files_output = self.format_attached_files(
                        attached_files, max_output_lines
                    )
                    if files_output:
                        output.append("")
                        output.append(files_output)
                
                output.append("-" * 40)
                output.append("")
            
            # Показываем ответы ИИ
            elif msg_type == 2 and text:
                output.append("🤖 ИИ:")
                output.append(text)
                
                # Token info for AI messages
                token_info = self.format_token_info(msg)
                if token_info:
                    output.append("")
                    output.append(token_info)
                
                output.append("-" * 40)
                output.append("")
            
            # Показываем мыслительный процесс ИИ
            elif is_thought:
                duration_seconds = thinking_duration / 1000.0  # Convert ms to seconds
                thinking_content = msg.get('thinking_content', '')

                # Determine if the thinking content is meaningful (i.e., not just encoded or raw JSON)
                is_meaningful_content = not (thinking_content.startswith('AVSoXO') or thinking_content.startswith('{'))

                if is_meaningful_content and thinking_content:
                    output.append(f"💭 ИИ: Мыслительный процесс ({duration_seconds:.1f}с)")
                    
                    # Apply line limiting to meaningful thinking content
                    thinking_lines = thinking_content.split('\n')
                    if max_output_lines > 0 and len(thinking_lines) > max_output_lines:
                        limited_lines = thinking_lines[:max_output_lines]
                        output.extend(limited_lines)
                        remaining_lines = len(thinking_lines) - max_output_lines
                        output.append(f"... ({remaining_lines} строк скрыто)")
                    else:
                        output.extend(thinking_lines)
                elif not is_meaningful_content and thinking_content:
                    # If it's encoded/structured but not meaningful, just show the duration line
                    output.append(f"💭 ИИ: Мыслительный процесс ({duration_seconds:.1f}с)")
                else:  # No thinking_content at all
                    output.append(f"💭 ИИ: Мыслительный процесс ({duration_seconds:.1f}с)")
                
                # Token info for thinking bubbles
                token_info = self.format_token_info(msg)
                if token_info:
                    output.append("")
                    output.append(token_info)
                
                output.append("-" * 40)
                output.append("")
            
            # Показываем вызовы инструментов
            elif tool_data:
                tool_output = self.format_tool_call(tool_data, max_output_lines)
                if tool_output:
                    output.append(tool_output)
                    
                    # Token info for tool calls
                    token_info = self.format_token_info(msg)
                    if token_info:
                        output.append("")
                        output.append(token_info)
                    
                    output.append("-" * 40)
                    output.append("")
            
            # Неизвестные типы
            elif text:
                output.append(f"❓ НЕИЗВЕСТНО (тип {msg_type}):")
                output.append(text)
                
                # Token info for unknown types
                token_info = self.format_token_info(msg)
                if token_info:
                    output.append("")
                    output.append(token_info)
                
                output.append("-" * 40)
                output.append("")
        
        # Add token summary at the end
        total_tokens = total_input_tokens + total_output_tokens
        if total_tokens > 0:
            output.append("=" * 60)
            output.append("📊 СВОДКА ПО ТОКЕНАМ")
            output.append("=" * 60)
            output.append(f"Всего токенов: {total_tokens}")
            output.append(f"  • Входящие токены: {total_input_tokens}")
            output.append(f"  • Исходящие токены: {total_output_tokens}")
            output.append(f"Сообщений с токенами: {messages_with_tokens}")
            output.append("")
        
        return "\n".join(output)
    
    def list_projects(self):
        """Показать список всех проектов"""
        projects = self.get_projects()
        
        print("ДОСТУПНЫЕ ПРОЕКТЫ:")
        print("=" * 50)
        
        for i, project in enumerate(projects, 1):
            latest = project['latest_dialog']
            if latest:
                last_updated = datetime.fromtimestamp(
                    latest.get('lastUpdatedAt', 0) / 1000
                )
                dialog_count = len(project['composers'])
                print(f"{i:2d}. {project['project_name']}")
                print(f"    Путь: {project['folder_path']}")
                print(f"    Диалогов: {dialog_count}")
                print(
                    f"    Последний диалог: {latest.get('name', 'Без названия')}"
                )
                print(
                    f"    Обновлен: {last_updated.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                print()
    
    def list_dialogs(self, project_name: str):
        """Показать список диалогов для проекта"""
        projects = self.get_projects()
        
        # Найти проект
        project = None
        for p in projects:
            if project_name.lower() in p['project_name'].lower():
                project = p
                break
        
        if not project:
            print(f"Проект '{project_name}' не найден")
            return
        
        print(f"ДИАЛОГИ В ПРОЕКТЕ: {project['project_name']}")
        print("=" * 50)
        
        composers = sorted(
            project['composers'],
            key=lambda x: x.get('lastUpdatedAt', 0),
            reverse=True
        )
        
        for i, composer in enumerate(composers, 1):
            last_updated = datetime.fromtimestamp(
                composer.get('lastUpdatedAt', 0) / 1000
            )
            created = datetime.fromtimestamp(
                composer.get('createdAt', 0) / 1000
            )
            
            dialog_name_to_display = composer.get('name', 'Без названия')
            print(f"{i:2d}. {dialog_name_to_display}")
            print(f"    ID: {composer['composerId']}")
            print(f"    Создан: {created.strftime('%Y-%m-%d %H:%M:%S')}")
            print(
                f"    Обновлен: {last_updated.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            print()
    
    def show_dialog(self, project_name: Optional[str] = None, 
                    dialog_name: Optional[str] = None, 
                    max_output_lines: int = 1):
        """Показать диалог"""
        projects = self.get_projects()
        
        if not projects:
            print("Проекты не найдены")
            return
        
        # Выбрать проект
        if project_name:
            project = None
            for p in projects:
                if project_name.lower() in p['project_name'].lower():
                    project = p
                    break
            if not project:
                print(f"Проект '{project_name}' не найден")
                return
        else:
            # Самый свежий проект
            project = projects[0]
        
        # Выбрать диалог
        if dialog_name:
            dialog = None
            for composer in project['composers']:
                composer_name = composer.get('name', '')
                if dialog_name.lower() in composer_name.lower():
                    dialog = composer
                    break
            if not dialog:
                print(
                    f"Диалог '{dialog_name}' не найден в проекте "
                    f"'{project['project_name']}'"
                )
                return
        else:
            # Самый свежий диалог
            if not project['composers']:
                print(f"В проекте '{project['project_name']}' нет диалогов")
                return
            dialog = max(
                project['composers'], key=lambda x: x.get('lastUpdatedAt', 0)
            )
        
        # Получить сообщения диалога
        try:
            messages = self.get_dialog_messages(dialog['composerId'])
            if not messages:
                dialog_name = dialog.get(
                    'name', f"Диалог {dialog['composerId'][:8]}"
                )
                print(f"Сообщения в диалоге '{dialog_name}' не найдены")
                return
            
            # Отобразить диалог
            dialog_name = dialog.get(
                'name', f"Диалог {dialog['composerId'][:8]}"
            )
            formatted_dialog = self.format_dialog(
                messages, dialog_name, project['project_name'], max_output_lines
            )
            print(formatted_dialog)
            
        except Exception:
            print("Ошибка при получении диалога")


def main():
    parser = argparse.ArgumentParser(
        description='Просмотр диалогов из базы данных Cursor IDE'
    )
    parser.add_argument(
        '--project', '-p', help='Название проекта (частичное совпадение)'
    )
    parser.add_argument(
        '--dialog', '-d', help='Название диалога (частичное совпадение)'
    )
    parser.add_argument(
        '--list-projects', action='store_true', help='Показать список проектов'
    )
    parser.add_argument(
        '--list-dialogs', help='Показать список диалогов для проекта'
    )
    parser.add_argument(
        '--max-output-lines', '-m', type=int, default=1,
        help=(
            'Максимальное количество строк для вывода результатов инструментов '
            'и прикрепленных файлов (по умолчанию: 1)'
        )
    )
    
    args = parser.parse_args()
    
    viewer = CursorChatViewer()
    
    if args.list_projects:
        viewer.list_projects()
    elif args.list_dialogs:
        viewer.list_dialogs(args.list_dialogs)
    else:
        viewer.show_dialog(args.project, args.dialog, args.max_output_lines)


if __name__ == "__main__":
    main()
