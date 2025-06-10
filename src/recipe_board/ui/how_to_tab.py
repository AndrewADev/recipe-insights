import gradio as gr


def create_how_to_tab():
    """Create the How-To tab with usage instructions."""
    with gr.Tab(label="How To") as how_to_tab:
        gr.Markdown(
            """
# 🍳 Welcome to Recipe Board!

## What is Recipe Board? 🤖

Recipe Board is an AI-powered recipe analysis tool that helps you understand the **dependencies** and **relationships** within your recipes! 🔍

Using advanced natural language processing and machine learning, Recipe Board can:
- 📝 **Parse ingredients** with amounts, units, and modifiers
- 🔧 **Identify equipment** and tools needed
- ⚡ **Extract cooking actions** and their dependencies
- 🕸️ **Visualize relationships** between ingredients, actions, and equipment
- 📊 **Export interactive graphs** for deeper analysis

Perfect for home cooks who want to better understand their recipes! 👨‍🍳👩‍🍳

## How to Use Recipe Board 📋

### Step 1: Choose Your Recipe 📖
- **Try a sample**: Select "Claude's Lasagne" from the dropdown to see the tool in action
- **Use the preview**: Click on any sample to see a preview before copying
- **Copy to input**: Hit "Copy to Input" to load the sample recipe
- **Or paste your own**: Simply paste any recipe text into the input box

### Step 2: Parse Your Recipe 🔄
- Click the **"Parse Recipe"** button to start the analysis
- **First stage**: Ingredients and equipment are extracted
- **Second stage**: Actions and dependencies are automatically parsed
- Watch the real-time status updates as parsing progresses!

### Step 3: Review the Results ✅
After parsing, you'll see three sections:
- **📝 Parsed Results**: Your ingredients and equipment, nicely formatted
- **⚡ Basic Actions**: Cooking verbs found in your recipe (mix, bake, combine, etc.)
- **🔗 Action Dependencies**: Which ingredients and equipment connect to each action

### Step 4: Visualize Dependencies 🎨
- Once parsing is complete, the **"Visualize Dependencies"** button becomes active
- Click it to automatically switch to the **Visualization tab**
- Explore the interactive graph showing:
  - 🟢 **Green circles**: Ingredients
  - 🔷 **Blue diamonds**: Actions
  - 🟠 **Orange squares**: Equipment
- Hover over nodes for detailed information!

### Step 5: Export Your Analysis 📥
From the visualization tab, you can:
- **Download as HTML**: Interactive graph you can share or save
- **Download as JSON**: Raw data for further analysis

## Give Us Feedback! 💭
Help us improve Recipe Board by using the feedback buttons:
- 👍 **Helpful**: When the analysis works well for your recipe
- 👎 **Not Helpful**: When something doesn't look right

*Your feedback helps train our AI to work better with diverse recipes!*

## Tips for Best Results 🎯
- **Clear formatting**: Recipes with clear structure work best. It can infer the ingredients without a dedicated section, but you will likely have better results if you have one.
- **Try samples first**: Start with our sample recipe to see how it works
- **Be patient**: Complex recipes may take a moment to analyze

Ready to dive into your recipe's hidden structure? Let's get cooking! 🚀
        """
        )

        # Add some visual spacing
        gr.HTML("<br>")

        # Big, prominent Get Started button
        with gr.Row():
            with gr.Column(scale=1):
                pass  # Empty column for centering
            with gr.Column(scale=2):
                get_started_button = gr.Button(
                    "🍽️ Get Started!",
                    variant="primary",
                    size="lg",
                    elem_classes=["get-started-btn"],
                )
            with gr.Column(scale=1):
                pass  # Empty column for centering

        gr.HTML("<br>")

    return get_started_button
