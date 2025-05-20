"""
Common styles for the user interface
"""

# Style for transfer buttons
TRANSFER_BUTTON_STYLE = """
    QPushButton {
        background-color: #00a0e9;
        color: white;
        border: none;
        border-radius: 3px;
        
        /* 3D effect with these borders only */
        border-top: 1px solid #33b5f4;
        border-left: 1px solid #33b5f4;
        border-right: 1px solid #0077b3;
        border-bottom: 1px solid #0077b3;
    }
    QPushButton:hover {
        background-color: #33b5f4;
    }
    QPushButton:pressed {
        background-color: #0088cc;
        border-top: 1px solid #0077b3;
        border-left: 1px solid #0077b3;
        border-right: 1px solid #33b5f4;
        border-bottom: 1px solid #33b5f4;
    }
"""

# Style for title labels
TITLE_LABEL_STYLE = "font-weight: bold; font-size: 14px;" 