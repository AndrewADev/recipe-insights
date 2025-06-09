import gradio as gr
from wasabi import msg

from recipe_board.agents.models import parse_recipe, parse_actions


def create_parser_tab():
    with gr.Tab(label="Parser"):
        gr.Markdown("# Recipe Board")
        gr.Markdown(
            "Paste your recipe text on the left and click 'Parse Recipe' to analyze ingredients and equipment."
        )

        with gr.Row():
            with gr.Column(scale=1):
                recipe_input = gr.Textbox(
                    label="Recipe Text",
                    placeholder="Paste your recipe here...\n\nExample:\n## Ingredients\n- 2 cups flour\n- 1 large onion, diced\n- 500g ground beef...",
                    lines=20,
                    max_lines=30,
                )

                parse_button = gr.Button("Parse Recipe", variant="primary", size="lg")
                parse_actions_button = gr.Button(
                    "Parse Actions", variant="secondary", size="lg", interactive=False
                )

            with gr.Column(scale=1):
                parsed_output = gr.Textbox(
                    label="Parsed Results",
                    placeholder="Parsed ingredients and equipment will appear here...",
                    lines=10,
                    max_lines=15,
                )

                actions_output = gr.Textbox(
                    label="Parsed Actions",
                    placeholder="Parsed actions will appear here after ingredients and equipment are processed...",
                    lines=10,
                    max_lines=15,
                )

        # Helper function to validate parsed JSON contains ingredients and equipment
        def is_valid_parsed_output(parsed_text):
            """Check if parsed output contains valid ingredients and equipment."""
            if not parsed_text or parsed_text.strip() == "":
                return False

            try:
                import json

                data = json.loads(parsed_text)

                # Check if it has the expected structure and non-empty arrays
                has_ingredients = (
                    "ingredients" in data
                    and isinstance(data["ingredients"], list)
                    and len(data["ingredients"]) > 0
                )
                has_equipment = (
                    "equipment" in data
                    and isinstance(data["equipment"], list)
                    and len(data["equipment"]) > 0
                )

                return has_ingredients and has_equipment
            except (json.JSONDecodeError, KeyError, TypeError):
                return False

        def parse_recipe_and_enable_actions(recipe_text):
            """Parse recipe and return both the result and button state."""
            parsed_result = parse_recipe(recipe_text)
            is_valid = is_valid_parsed_output(parsed_result)

            return parsed_result, gr.update(interactive=is_valid)

        def parse_actions_from_parsed_data(recipe_text, parsed_data):
            """Parse actions from already parsed ingredients and equipment."""
            if not is_valid_parsed_output(parsed_data):
                return "Error: Invalid or missing ingredient/equipment data. Please parse recipe first."

            try:
                # Call the actual parse_actions function
                actions_result = parse_actions(recipe_text, parsed_data)
                return actions_result
            except ValueError as e:
                return f"Error parsing actions: {str(e)}"
            except Exception as e:
                msg.fail(f"Unexpected error in actions parsing: {e}")
                return f"Unexpected error occurred while parsing actions: {str(e)}"

        parse_button.click(
            fn=parse_recipe_and_enable_actions,
            inputs=[recipe_input],
            outputs=[parsed_output, parse_actions_button],
        )

        parse_actions_button.click(
            fn=parse_actions_from_parsed_data,
            inputs=[recipe_input, parsed_output],
            outputs=[actions_output],
        )

        # Feedback components

        with gr.Group():
            gr.Markdown("### Feedback")
            gr.Markdown(
                "_By submitting feedback, you agree to your prompt and parsed data will be stored for analysis._"
            )
            with gr.Row():
                helpful_btn = gr.Button("👍 Helpful", size="sm")
                not_helpful_btn = gr.Button("👎 Not Helpful", size="sm")

        feedback_status = gr.Textbox(label="", visible=False)

        def handle_feedback(feedback_type, recipe_input, parsed_output, actions_output):
            import json
            import datetime
            import os

            # Ensure flagged directory exists
            os.makedirs("flagged", exist_ok=True)

            feedback_data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "feedback": feedback_type,
                "input": recipe_input,
                "output": parsed_output,
                "actions": actions_output,
            }

            # Save to flagged directory with timestamp
            filename = f"flagged/feedback_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, "w") as f:
                json.dump(feedback_data, f, indent=2)

            msg.info(f"User feedback saved to {filename}: {feedback_type}")
            return gr.update(
                value=f"Thanks! Feedback recorded: {feedback_type}", visible=True
            )

        helpful_btn.click(
            fn=lambda recipe_input, parsed_output, actions_output: handle_feedback(
                "helpful", recipe_input, parsed_output, actions_output
            ),
            inputs=[recipe_input, parsed_output, actions_output],
            outputs=[feedback_status],
        )
        not_helpful_btn.click(
            fn=lambda recipe_input, parsed_output, actions_output: handle_feedback(
                "not_helpful", recipe_input, parsed_output, actions_output
            ),
            inputs=[recipe_input, parsed_output, actions_output],
            outputs=[feedback_status],
        )


def create_ui():
    """Create and configure the Gradio interface."""
    with gr.Blocks(title="Recipe Board - AI Recipe Analyzer") as demo:
        create_parser_tab()

    return demo


def launch_ui(share=False, server_port=7860):
    """Launch the Gradio interface."""
    demo = create_ui()
    demo.launch(share=share, server_port=server_port)


if __name__ == "__main__":
    launch_ui()
