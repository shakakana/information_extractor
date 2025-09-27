"""
LLM client utilities for chat and batch workflows.

Provides:
- BaseLLMClient: HTTP request helper with auth headers and JSON handling.
- LLMChatProcessor: single-conversation manager supporting message history,
  GUID tracking, simple chat interface, and configurable model/temperature.
- LLMBatchProcessor: batch submission and management (create, poll, results,
  metadata, input, errors, cancel, delete) with async wait/poll utilities
  and NDJSON parsing for batch results.

Intended for integration with a UDAL-backed LLM API; uses settings for defaults
and loguru for structured logging.
"""

import json
import requests
import uuid
import time
import asyncio
from typing import List, Dict, Any, Optional, Callable
from src.core.config import settings
from loguru import logger


class BaseLLMClient:
    """Base class with common functionality for LLM API interactions."""

    def __init__(
        self,
        udal_pat: str = None,
        base_url: str = None,
    ):
        self.udal_pat = udal_pat or settings.UDAL_PAT
        self.base_url = base_url.rstrip("/") if base_url else None
        self.headers = {
            "accept": "application/json",
            "Authorization": f"Basic {self.udal_pat}",
        }
        logger.debug("BaseLLMClient initialized with base_url: {}", self.base_url)

    def _is_gpt_five_or_above(self, model: str) -> bool:
        """Check if model is GPT-5 or above."""
        if not model:
            return False
        return "gpt-5" in model.lower()

    def _make_request(
        self, method: str, endpoint: Optional[str], data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make a request to the API."""
        endpoint = endpoint or ""
        url = f"{self.base_url}/{endpoint.lstrip('/')}" if endpoint else self.base_url
        headers = self.headers.copy()

        if method.upper() == "POST" and data:
            headers["Content-type"] = "application/json"

        logger.debug("Making {} request to: {}", method.upper(), url)

        try:
            response = requests.request(method, url, headers=headers, json=data)
            response.raise_for_status()

            logger.debug("Request successful, status code: {}", response.status_code)

            # Check if response is JSON
            try:
                json_response = response.json()
                logger.debug("Response type: {}", type(json_response).__name__)
                return json_response
            except ValueError as json_error:
                # If JSON parsing fails, log the raw response and raise
                logger.error("Failed to parse JSON response: {}", json_error)
                logger.error("Raw response text: {}", response.text)
                raise ValueError(f"Invalid JSON response: {response.text}")

        except requests.RequestException as e:
            logger.error("API request failed: {}", e)
            if hasattr(e, "response") and e.response is not None:
                logger.error(
                    "Response status: {}", getattr(e.response, "status_code", "Unknown")
                )
                logger.error(
                    "Response text: {}", getattr(e.response, "text", "No response text")
                )
            raise


class LLMChatProcessor(BaseLLMClient):
    """Class for individual chat processing operations."""

    def __init__(
        self,
        udal_pat: str = settings.UDAL_PAT,
        model: str = settings.MODEL,
        base_url: str = settings.LLM_CHAT_ENDPOINT,
    ):
        super().__init__(udal_pat=udal_pat, base_url=base_url)
        self.model = model
        self.conversation_history = []
        self.conversation_guid = None

        logger.info("LLMChatProcessor initialized with model: {}", self.model)

    def process_message(
        self,
        content: str,
        role: str = "user",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        conversation_mode: List[str] = ["default"],
        conversation_source: str = "bcai-api-system-identifier",
        stream: Optional[bool] = False,
        response_format: Optional[Dict] = None,
        **kwargs,  # For any additional API parameters
    ) -> str:
        """Submit prompt, manage conversation history, and return response."""

        # Add message to history
        self.conversation_history.append({"role": role, "content": content})

        # Required by API
        if not self.conversation_guid:
            self.conversation_guid = str(uuid.uuid4())

        final_model = model or self.model
        if self._is_gpt_five_or_above(final_model):
            if temperature is not None:
                logger.warning(
                    "Temperature parameter ignored for model {} (GPT-5+ models don't support temperature)",
                    final_model,
                )

        data = {
            "messages": self.conversation_history,
            "model": final_model,
            "conversation_guid": self.conversation_guid,
            "conversation_mode": conversation_mode,
            "conversation_source": conversation_source,
            "stream": stream,
        }

        if response_format is not None:
            data["response_format"] = response_format

        # Add optional API parameters if provided
        data.update(kwargs)

        try:
            response = self._make_request(method="POST", endpoint=None, data=data)

            # Extract and store assistant response
            assistant_message = response.get("message", {}).get("content", "")

            # JSON validation if response_format is json_object
            if (
                response_format
                and response_format.get("type") == "json_object"
                and assistant_message
            ):
                try:
                    json.loads(assistant_message)
                except json.JSONDecodeError:
                    logger.warning("Expected JSON response but got invalid JSON")

            self.conversation_history.append(
                {"role": "assistant", "content": assistant_message}
            )

            logger.info(
                "Prompt submitted successfully, GUID: {}", self.conversation_guid
            )

            # Store conversation_guid for subsequent requests
            if not self.conversation_guid:
                self.conversation_guid = response.get("conversation_guid")

            return response
        except Exception as e:
            logger.error("Failed to submit prompt: {}", e)
            raise

    def get_history(self) -> List[Dict[str, str]]:
        """Get full conversation history."""
        return self.conversation_history.copy()

    def clear_history(self) -> None:
        """Clear conversation history and start fresh."""
        self.conversation_history = []
        self.conversation_guid = None

    def chat(self, message: str) -> str:
        """Simple chat method using all defaults."""
        return self.process_message(message)


class LLMBatchProcessor(BaseLLMClient):
    """Class for batch processing operations."""

    def __init__(
        self,
        udal_pat: str = settings.UDAL_PAT,
        model: str = settings.MODEL,
        base_url: str = settings.LLM_BATCH_ENDPOINT,
    ):
        super().__init__(udal_pat=udal_pat, base_url=base_url)
        self.model = model
        self.batch_client = BaseLLMClient(udal_pat, base_url)
        logger.info("LLMBatchProcessor initialized with model: {}", self.model)

    def create_batch(
        self,
        batch_items: List[str],
        model: Optional[str] = None,
        conversation_mode: Optional[List[str]] = ["default"],
        conversation_source: str = "bcai-api-system-identifier",
        temperature: Optional[float] = None,
        custom_ids: List[str] = None,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Create chats for multiple requests in a batch."""
        logger.info("Creating batch with {} prompts", len(batch_items))

        # Ensure that any custom IDs are the same length as batch_items
        if custom_ids is not None:
            if len(custom_ids) != len(batch_items):
                logger.error(
                    "Failed to create batch: Custom ID length is not the same as batch item length"
                )
                raise Exception()
            elif len(set(custom_ids)) != len(custom_ids):
                logger.error("Failed to create batch: Custom ID list is not unique")
                raise Exception()

        formatted_items = []
        for i, prompt in enumerate(batch_items):
            if custom_ids is None:
                custom_id = str(uuid.uuid4())
            else:
                custom_id = custom_ids[i]

            body = {
                "messages": [{"role": "user", "content": prompt}],
                "model": model or self.model,
                "conversation_mode": conversation_mode,
                "conversation_source": conversation_source,
                "temperature": temperature,
            }

            if response_format is not None:
                body["response_format"] = response_format

            formatted_items.append({"custom_id": custom_id, "body": body})
            logger.debug("Added batch item with custom_id: {}", custom_id)

        data = {"batch_items": formatted_items}

        try:
            response = self._make_request("POST", "conversation", data)
            batch_id = response.get("id") or response.get("batch_id")
            logger.info("Batch created successfully with ID: {}", batch_id)
            return response
        except Exception as e:
            logger.error("Failed to create batch: {}", e)
            raise

    async def submit_and_wait_for_results(
        self,
        batch_items: List[str],
        poll_interval: int = 30,
        max_wait: int = 3600,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        **kwargs,  # For any additional create_batch parameters
    ) -> Dict[str, Any]:
        """
        Submit batch job and wait for completion, then return results.

        Args:
            batch_items: List of prompts strings
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait for completion
            progress_callback: Optional callback for progress updates (status, completed, total)
            **kwargs: Additional parameters passwed to create_batch

        Returns:
            Dict containing the batch results
        """
        logger.info(
            "Submitting batch with {} items, poll_interval={}s, max_wait={}s",
            len(batch_items),
            poll_interval,
            max_wait,
        )

        # Create batch
        response = await asyncio.to_thread(self.create_batch, batch_items, **kwargs)
        batch_id = response.get("id") or response.get("batch_id")

        if not batch_id:
            logger.error("No batch_id found in response: {}", response)
            raise ValueError(f"No batch_id found in response: {response}")

        logger.info(
            "Batch job created with ID: {}, waiting for completion...", batch_id
        )

        # Wait for completion
        await self.wait_for_completion(
            batch_id, poll_interval, max_wait, progress_callback
        )

        # Return results
        logger.info("Batch completed, retrieving results for batch: {}", batch_id)
        return await asyncio.to_thread(self.get_batch_results, batch_id)

    async def wait_for_completion(
        self,
        batch_id: str,
        poll_interval: int = 30,
        max_wait: int = 3600,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        """
        Wait for batch job to complete by polling status.

        Args:
            batch_id: The batch job ID to monitor
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait
            progress_callback: Optional callback for progress updates
        """
        start_time = time.time()
        logger.info("Starting to monitor batch {} completion", batch_id)

        while time.time() - start_time < max_wait:
            try:
                metadata = await asyncio.to_thread(self.get_batch_metadata, batch_id)
                status = metadata.get("status", "unknown").lower()
                completed_count = metadata.get("completed_count", 0)
                total_count = metadata.get("request_count", 0)

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(status, completed_count, total_count)
                else:
                    logger.info(
                        "Batch {} status: {} ({}/{})",
                        batch_id,
                        status,
                        completed_count,
                        total_count,
                    )

                if status in ["completed"]:
                    logger.success("Batch {} completed successfully", batch_id)
                    return
                elif status in ["failed", "cancelled", "expired"]:
                    logger.error("Batch {} failed with status: {}", batch_id, status)
                    raise RuntimeError(
                        f"Batch job {batch_id} failed with status: {status}"
                    )

                await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.error("Error checking batch status for {}: {}", batch_id, e)
                await asyncio.sleep(poll_interval)

        logger.error("Batch {} did not complete within {} seconds", batch_id, max_wait)
        raise TimeoutError(
            f"Batch job {batch_id} did not complete within {max_wait} seconds"
        )

    def get_models(self, endpoint: str = "batch") -> List[Dict[str, Any]]:
        """Retrieve a list of all models available."""
        logger.debug("Retrieving available models")
        try:
            result = self.batch_client._make_request("GET", "getModels")
            logger.info(
                "Retrieved {} available models",
                len(result) if isinstance(result, list) else "unknown",
            )
            return result
        except Exception as e:
            logger.error("Failed to retrieve models: {}", e)
            raise

    def list_batch_jobs(self) -> List[Dict[str, Any]]:
        """Retrieve a list of all batch jobs submitted by the user."""
        logger.debug("Retrieving list of batch jobs")
        try:
            result = self.batch_client._make_request("GET", "list")
            logger.info(
                "Retrieved {} batch jobs",
                len(result) if isinstance(result, list) else "unknown",
            )
            return result
        except Exception as e:
            logger.error("Failed to list batch jobs: {}", e)
            raise

    def get_batch_metadata(self, batch_id: str) -> Dict[str, Any]:
        """Retrieve the metadata of a specific batch job by its ID."""
        logger.debug("Retrieving metadata for batch: {}", batch_id)
        try:
            result = self.batch_client._make_request("GET", batch_id)
            logger.debug(
                "Retrieved metadata for batch {}: status={}",
                batch_id,
                result.get("status", "unknown"),
            )
            return result
        except Exception as e:
            logger.error("Failed to get metadata for batch {}: {}", batch_id, e)
            raise

    import json

    def get_batch_results(self, batch_id: str) -> Dict[str, Any]:
        """Retrieve and parse the results of a batch job by its ID."""
        logger.debug("Retrieving results for batch: {}", batch_id)
        try:
            raw_result = self.batch_client._make_request("GET", f"{batch_id}/result")

            # If _make_request returns a string (raw NDJSON), parse it
            if isinstance(raw_result, str):
                # Split by newline and parse each JSON object
                json_strings = [line for line in raw_result.split("
") if line.strip()]
                parsed_results = []
                for json_str in json_strings:
                    try:
                        parsed = json.loads(json_str)
                        parsed_results.append(parsed)
                    except json.JSONDecodeError as e:
                        logger.error(
                            "Failed to parse JSON line in batch results: {} - Line: {}",
                            e,
                            json_str,
                        )
                result_count = len(parsed_results)
                logger.info("Parsed {} results for batch {}", result_count, batch_id)
                return {
                    "results": parsed_results,
                    "result_count": result_count,
                }

            # If already a dict (normal JSON), handle it
            elif isinstance(raw_result, dict):
                result_count = len(raw_result.get("results", []))
                logger.info("Retrieved {} results for batch {}", result_count, batch_id)
                return raw_result

            else:
                logger.error(
                    "Unexpected type for batch results: {} (batch {})",
                    type(raw_result).__name__,
                    batch_id,
                )
                return {
                    "results": [],
                    "result_count": 0,
                    "raw_result": raw_result,
                }

        except Exception as e:
            logger.error("Failed to get results for batch {}: {}", batch_id, e)
            raise

    def get_batch_input(self, batch_id: str) -> Dict[str, Any]:
        """Retrieve the input of a specific batch job by its ID."""
        logger.debug("Retrieving input for batch: {}", batch_id)
        try:
            result = self.batch_client._make_request("GET", f"{batch_id}/input")
            logger.debug("Retrieved input for batch: {}", batch_id)
            return result
        except Exception as e:
            logger.error("Failed to get input for batch {}: {}", batch_id, e)
            raise

    def get_batch_errors(self, batch_id: str) -> Dict[str, Any]:
        """Retrieve the errors of a specific batch job by its ID."""
        logger.debug("Retrieving errors for batch: {}", batch_id)
        try:
            result = self.batch_client._make_request("GET", f"{batch_id}/errors")
            error_count = (
                len(result.get("errors", [])) if "errors" in result else "unknown"
            )
            logger.info(
                "Retrieved errors for batch {}: {} errors", batch_id, error_count
            )
            return result
        except Exception as e:
            logger.error("Failed to get errors for batch {}: {}", batch_id, e)
            raise

    def cancel_batch_job(self, batch_id: str) -> Dict[str, Any]:
        """Cancel a batch job by its ID."""
        logger.info("Cancelling batch job: {}", batch_id)
        try:
            result = self.batch_client._make_request("DELETE", f"{batch_id}/cancel")
            logger.info("Successfully cancelled batch: {}", batch_id)
            return result
        except Exception as e:
            logger.error("Failed to cancel batch {}: {}", batch_id, e)
            raise

    def delete_batch_results(self, batch_id: str) -> Dict[str, Any]:
        """Delete a batch job's result file."""
        logger.info("Deleting results for batch: {}", batch_id)
        try:
            result = self.batch_client._make_request("DELETE", f"{batch_id}/result")
            logger.info("Successfully deleted results for batch: {}", batch_id)
            return result
        except Exception as e:
            logger.error("Failed to delete results for batch {}: {}", batch_id, e)
            raise

    def delete_batch_errors(self, batch_id: str) -> Dict[str, Any]:
        """Delete a batch job's error file."""
        logger.info("Deleting errors for batch: {}", batch_id)
        try:
            result = self.batch_client._make_request("DELETE", f"{batch_id}/error")
            logger.info("Successfully deleted errors for batch: {}", batch_id)
            return result
        except Exception as e:
            logger.error("Failed to delete errors for batch {}: {}", batch_id, e)
            raise
