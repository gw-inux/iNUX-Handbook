---
title: Streamlit
layout: home
nav_order: 5
parent: Electronic Questions
has_children: false
---

<script
  src="https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML"
  type="text/javascript">
</script>

## Streamlit Question Types

| Question Type                                                              | Question Description |
|----------------------------------------------------------------------------|----------------------|
| Checkbox (`st.checkbox`)                                                   | Presents a box that users can tick or leave blank. Useful for binary yes/no or agree/disagree questions. |
| Radio Button (`st.radio`)                                                  | Allows users to select one option from a list of choices. Ideal for multiple-choice questions where only one answer is allowed. |
| Selectbox (`st.selectbox`)                                                 | A dropdown menu letting users pick a single option from a list. Similar in use to radio buttons but saves screen space. |
| Multiselect (`st.multiselect`)                                             | Lets users pick multiple options from a dropdown menu. Perfect for questions where more than one answer may apply. |
| Slider (`st.slider`) & Select Slider (`st.select_slider`)                  | Sliders allow users to select a numeric value or a value from an ordered list by dragging a bar. Useful for ratings, age, or scale-based questions. |
| Number Input (`st.number_input`)                                           | Lets users enter or adjust a number within defined bounds. Suitable for quantitative feedback (e.g., "How many hours per week?"). |
| Text Input (`st.text_input`) & Text Area (`st.text_area`)                  | Single-line field for short responses (names, email, brief answers). Multi-line field for longer free-text feedback or explanations. |
| Date Input (`st.date_input`) & Time Input (`st.time_input`)                | Specialized pickers for selecting a date or time. Ideal for questions about scheduling or dates of events. |
| Toggle (`st.toggle`)                                                       | Simple switch for on/off, true/false questions. |
| Feedback (`st.feedback`)                                                   | Provides a quick star rating or icon-based feedback option for gauging user sentiment or satisfaction. |
| Pills & Segmented Control (`st.pills`, `st.segmented_control`)             | Modern, visually appealing selection widgets for choosing one among several categories or tags. |
| Chat Input (`st.chat_input`)                                               | Field designed for capturing user responses in a chat-style or conversational questionnaire. |

