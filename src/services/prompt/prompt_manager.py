"""
Prompt Manager Service

This service manages the retrieval and formatting of prompts for the LLM service.
"""

from typing import Dict
from loguru import logger
from src.services.prompt.templates import ALL_PROMPTS


class PromptManager:
    """
    Service for managing and formatting prompts for the LLM service.
    """

    def __init__(self):
        """Initialize the prompt manager with the default prompt templates."""
        self.templates = ALL_PROMPTS
        self.custom_templates = {}
        logger.info(
            "PromptManager initialized with {} template categories", len(self.templates)
        )

    def get_prompt(self, category: str, prompt_type: str, **kwargs) -> str:
        """
        Retrieve and format a prompt template.

        Args:
            category: The category of the prompt (e.g., 'conversation')
            prompt_type: The specific prompt type within the category (e.g., 'greeting')
            **kwargs: Variables to format the prompt template with

        Returns:
            The formatted prompt

        Raises:
        ValueError: If the specified prompt template doesn't exist
        """
        try:
            # Check custom templates first
            if (
                category in self.custom_templates
                and prompt_type in self.custom_templates[category]
            ):
                template = self.custom_templates[category][prompt_type]
                logger.debug("Using custom template: {}/{}", category, prompt_type)
            # Then check built-in templates
            elif category in self.templates and prompt_type in self.templates[category]:
                template = self.templates[category][prompt_type]
                logger.debug("Using built-in template: {}/{}", category, prompt_type)
            else:
                logger.error("Prompt template not found: {}/{}", category, prompt_type)
                raise ValueError(f"Prompt template not found: {category}/{prompt_type}")

            # Format the template with the provided variables
            formatted_prompt = template.format(**kwargs)
            logger.debug(
                "Generated prompt for {}/{} with {} variables",
                category,
                prompt_type,
                len(kwargs),
            )
            return formatted_prompt

        except KeyError as e:
            logger.error(
                "Missing required variable for prompt template {}/{}: {}",
                category,
                prompt_type,
                e,
            )
            raise ValueError(f"Missing required variable for prompt template: {e}")
        except Exception as e:
            logger.error(
                "Error formatting prompt template {}/{}: {}", category, prompt_type, e
            )
            raise

    def add_custom_prompt(self, category: str, prompt_type: str, template: str) -> None:
        """
        Add a custom prompt template.

        Args:
            category: The category for the prompt
            prompt_type: The type name for the prompt
            template: The prompt template string
        """
        if category not in self.custom_templates:
            self.custom_templates[category] = {}

        self.custom_templates[category][prompt_type] = template
        logger.info("Added custom prompt template: {}/{}", category, prompt_type)

    def get_available_prompts(self) -> Dict[str, Dict[str, str]]:
        """
        Get a list of all available prompt templates.

        Returns:
            Dict[str, Dict[str, str]]: A nested dictionary of all prompt templates
        """
        # Combine built-in and custom templates
        all_templates = {}

        all_categories = set(
            list(self.templates.keys()) + list(self.custom_templates.keys())
        )

        for category in all_categories:
            all_templates[category] = {}

            # Add built-in templates for this category
            if category in self.templates:
                for prompt_type in self.templates[category]:
                    all_templates[category][prompt_type] = self.templates[category][
                        prompt_type
                    ]

            # Add custom templates for this category (these will override built-in if same name)
            if category in self.custom_templates:
                for prompt_type in self.custom_templates[category]:
                    all_templates[category][prompt_type] = self.custom_templates[
                        category
                    ][prompt_type]

        logger.debug(
            "Retrieved {} template categories with {} total templates",
            len(all_templates),
            sum(len(templates) for templates in all_templates.values()),
        )

        return all_templates

    def list_categories(self) -> list[str]:
        """
        Get a list of all available template categories.

        Returns:
            List of category names
        """
        categories = set(
            list(self.templates.keys()) + list(self.custom_templates.keys())
        )
        return sorted(list(categories))

    def list_prompts_in_category(self, category: str) -> list[str]:
        """
        Get a list of all prompt types in a specific category.

        Args:
            category: The category to list prompts for

        Returns:
            List of prompt type names in the category
        """
        prompts = set()

        # Add built-in prompts
        if category in self.templates:
            prompts.update(self.templates[category].keys())

        # Add custom prompts
        if category in self.custom_templates:
            prompts.update(self.custom_templates[category].keys())

        return sorted(list(prompts))

    def remove_custom_prompt(self, category: str, prompt_type: str) -> bool:
        """
        Remove a custom prompt template.

        Args:
            category: The category of the prompt
            prompt_type: The type name of the prompt

        Returns:
            True if the prompt was removed, False if it didn't exist
        """
        if (
            category in self.custom_templates
            and prompt_type in self.custom_templates[category]
        ):
            del self.custom_templates[category][prompt_type]

            # Clean up empty categories
            if not self.custom_templates[category]:
                del self.custom_templates[category]

            logger.info("Removed custom prompt template: {}/{}", category, prompt_type)
            return True

        logger.warning(
            "Custom prompt template not found for removal: {}/{}", category, prompt_type
        )
        return False
