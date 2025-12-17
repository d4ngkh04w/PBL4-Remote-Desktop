import logging
import os
import uuid
from datetime import datetime
from threading import Thread, Event
import time

from client.handlers.send_handler import SendHandler

logger = logging.getLogger(__name__)

# Chunk size: 256KB
CHUNK_SIZE = 256 * 1024


class FileTransferService:
    """Service to handle file transfers with chunking"""

    # Dictionary to track pending file transfers waiting for accept
    # Format: {file_id: {"session_id": str, "file_path": str, "filesize": int, "event": Event}}
    _pending_transfers = {}

    @staticmethod
    def send_file(session_id: str, file_path: str, sender_role: str):
        """Send a file in chunks"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False

            file_id = str(uuid.uuid4())
            filename = os.path.basename(file_path)
            filesize = os.path.getsize(file_path)

            # Send file metadata
            SendHandler.send_file_metadata_packet(
                session_id=session_id,
                file_id=file_id,
                filename=filename,
                filesize=filesize,
                sender_role=sender_role,
            )

            # Store transfer info and wait for accept before sending chunks
            accept_event = Event()
            FileTransferService._pending_transfers[file_id] = {
                "session_id": session_id,
                "file_path": file_path,
                "filesize": filesize,
                "event": accept_event,
            }

            logger.info(f"File metadata sent for {filename}, waiting for accept...")

            return file_id

        except Exception as e:
            logger.error(f"Error sending file: {e}", exc_info=True)
            return None

    @staticmethod
    def _send_chunks(session_id: str, file_id: str, file_path: str, filesize: int):
        """Send file chunks (runs in background thread)"""
        try:
            total_chunks = (filesize + CHUNK_SIZE - 1) // CHUNK_SIZE

            with open(file_path, "rb") as f:
                for chunk_index in range(total_chunks):
                    chunk_data = f.read(CHUNK_SIZE)

                    if not chunk_data:
                        break

                    SendHandler.send_file_chunk_packet(
                        session_id=session_id,
                        file_id=file_id,
                        chunk_index=chunk_index,
                        chunk_data=chunk_data,
                        total_chunks=total_chunks,
                    )

                    time.sleep(0.01)

            SendHandler.send_file_complete_packet(
                session_id=session_id, file_id=file_id, success=True
            )
            logger.info(f"File {file_id} sent")

        except Exception as e:
            logger.error(f"Error sending chunks for file {file_id}: {e}", exc_info=True)
            SendHandler.send_file_complete_packet(
                session_id=session_id,
                file_id=file_id,
                success=False,
                message=str(e),
            )

    @staticmethod
    def start_sending_chunks(file_id: str):
        """Start sending chunks after file is accepted"""
        transfer = FileTransferService._pending_transfers.get(file_id)
        if not transfer:
            logger.warning(f"Transfer {file_id} not found in pending transfers")
            return False

        # Start sending chunks in a background thread
        thread = Thread(
            target=FileTransferService._send_chunks,
            args=(
                transfer["session_id"],
                file_id,
                transfer["file_path"],
                transfer["filesize"],
            ),
            daemon=True,
        )
        thread.start()

        # Remove from pending after starting
        del FileTransferService._pending_transfers[file_id]

        logger.info(f"Started sending chunks for file {file_id}")
        return True

    @staticmethod
    def cancel_transfer(file_id: str):
        """Cancel a pending file transfer"""
        if file_id in FileTransferService._pending_transfers:
            del FileTransferService._pending_transfers[file_id]
            logger.info(f"Canceled file transfer {file_id}")
            return True
        return False

    @staticmethod
    def send_chat_message(session_id: str, sender_role: str, message: str):
        """Send a chat message"""
        try:
            timestamp = datetime.now().timestamp()
            SendHandler.send_chat_message_packet(
                session_id=session_id,
                sender_role=sender_role,
                message=message,
                timestamp=timestamp,
            )
            return True
        except Exception as e:
            logger.error(f"Error sending chat message: {e}", exc_info=True)
            return False
