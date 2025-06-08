import gradio as gr
from wasabi import msg

from recipe_board.agents.models import parse_recipe_equipment


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

            with gr.Column(scale=1):
                parsed_output = gr.Textbox(
                    label="Parsed Results",
                    placeholder="Parsed ingredients and equipment will appear here...",
                    lines=20,
                    max_lines=30,
                )

        # Wire up the parsing function
        parse_button.click(
            fn=parse_recipe_equipment, inputs=[recipe_input], outputs=[parsed_output]
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

        def handle_feedback(feedback_type, recipe_input, parsed_output):
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
            fn=lambda recipe_input, parsed_output: handle_feedback(
                "helpful", recipe_input, parsed_output
            ),
            inputs=[recipe_input, parsed_output],
            outputs=[feedback_status],
        )
        not_helpful_btn.click(
            fn=lambda recipe_input, parsed_output: handle_feedback(
                "not_helpful", recipe_input, parsed_output
            ),
            inputs=[recipe_input, parsed_output],
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
