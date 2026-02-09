"""Send file tool for sending files to users."""

from pathlib import Path
from typing import Any, Callable, Awaitable

from nanobot.agent.tools.base import Tool
from nanobot.bus.events import OutboundMessage


class SendFileTool(Tool):
    """Tool to send files to users on chat channels."""
    
    def __init__(
        self, 
        send_callback: Callable[[OutboundMessage], Awaitable[None]] | None = None,
        default_channel: str = "",
        default_chat_id: str = "",
        allowed_dir: Path | None = None
    ):
        self._send_callback = send_callback
        self._default_channel = default_channel
        self._default_chat_id = default_chat_id
        self._allowed_dir = allowed_dir
    
    def set_context(self, channel: str, chat_id: str) -> None:
        """Set the current message context."""
        self._default_channel = channel
        self._default_chat_id = chat_id
    
    def set_send_callback(self, callback: Callable[[OutboundMessage], Awaitable[None]]) -> None:
        """Set the callback for sending messages."""
        self._send_callback = callback
    
    @property
    def name(self) -> str:
        return "send_file"
    
    @property
    def description(self) -> str:
        return (
            "Send one or more files to the user. "
            "Supports images, documents, audio, and other file types. "
            "Use this when you want to share files with the user."
        )
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths to send (can be a single file or multiple files)"
                },
                "caption": {
                    "type": "string",
                    "description": "Optional caption/description for the file(s)"
                },
                "channel": {
                    "type": "string",
                    "description": "Optional: target channel (telegram, discord, etc.)"
                },
                "chat_id": {
                    "type": "string",
                    "description": "Optional: target chat/user ID"
                }
            },
            "required": ["file_paths"]
        }
    
    async def execute(
        self, 
        file_paths: list[str],
        caption: str = "",
        channel: str | None = None, 
        chat_id: str | None = None,
        **kwargs: Any
    ) -> str:
        channel = channel or self._default_channel
        chat_id = chat_id or self._default_chat_id
        
        if not channel or not chat_id:
            return "Error: No target channel/chat specified"
        
        if not self._send_callback:
            return "Error: File sending not configured"
        
        if not file_paths:
            return "Error: No file paths provided"
        
        # Validate file paths
        validated_paths = []
        for file_path_str in file_paths:
            try:
                file_path = Path(file_path_str).expanduser().resolve()
                
                # Check directory restriction if configured
                if self._allowed_dir:
                    allowed = self._allowed_dir.resolve()
                    if not str(file_path).startswith(str(allowed)):
                        return f"Error: File {file_path_str} is outside allowed directory {self._allowed_dir}"
                
                # Check if file exists
                if not file_path.exists():
                    return f"Error: File not found: {file_path_str}"
                
                if not file_path.is_file():
                    return f"Error: Not a file: {file_path_str}"
                
                validated_paths.append(str(file_path))
                
            except Exception as e:
                return f"Error validating file path {file_path_str}: {str(e)}"
        
        msg = OutboundMessage(
            channel=channel,
            chat_id=chat_id,
            content=caption,
            files=validated_paths
        )
        
        try:
            await self._send_callback(msg)
            file_count = len(validated_paths)
            files_desc = f"{file_count} file(s)" if file_count > 1 else validated_paths[0]
            return f"Successfully sent {files_desc} to {channel}:{chat_id}"
        except Exception as e:
            return f"Error sending file(s): {str(e)}"
