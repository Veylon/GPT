import openai
import json
import datetime
import hashlib
import html
import os
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from tkinter.messagebox import showerror
from transformers import GPT2TokenizerFast
# from gtts import gTTS
# from playsound import playsound
import threading
import time

# Load API Key
print("Loading API Key")
key_file = open("key.txt", "r")
openai.api_key = key_file.read()
key_file.close()
# Chat Log
history = []
last_system_text = ''
# Streamed text
fulltext = ''
response = None


def models():
    data_dict = json.loads(str(openai.Model.list()))
    out = []
    for m in data_dict["data"]:
        if m["id"].startswith("gpt"):
            out.append(m["id"])
    return out

# TTS
# tts_engine = pyttsx3.init()
# TTS Voice
# tts_voices = tts_engine.getProperty("voices")
# tts_engine.setProperty("voice", tts_voices[1].id)
# tts_engine.setProperty("rate", 150)

date_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
# Session Hash
sha256 = hashlib.sha256()
sha256.update(date_time.encode('utf-8'))
# Moderation Categories
categories = {0: "Hate", 1: "Threat", 2: "Self-Harm", 3: "Sexual", 4: "Minors", 5: "Violence", 6: "Graphic"}
# Tokenizer
tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
# Keeps track of the countdown to calculate the number of tokens
token_count_job = None

# GUI
main_height = 28
main_cols = 12
# Window Setup
print("Setting up GUI")
root = Tk()
root.title("GPT 3.5 Interface: Session " + str(sha256.hexdigest()).upper())
root.option_add("*font", "lucida 16")
root.resizable(False,False)
# Models
print("Getting Models")
label = Label(root, text="Model")
label.grid(row=1, column=main_cols)
box_models = ttk.Combobox(root, width=15, state="readonly", values=models())
# box_models = ttk.Combobox(root, width=15, state="readonly", values=["text-davinci-003", "text-chat-davinci-002-20221122", "text-curie-001", "code-cushman-001"])
box_models.set("gpt-3.5-turbo")
box_models.grid(row=2, column=main_cols, padx=5, pady=1)
# Tokens
label = Label(root, text="Tokens")
label.grid(row=3, column=main_cols)
text_tokens = Entry(root, width=5)
text_tokens.grid(row=4, column=main_cols)
text_tokens.insert(END, "4096")
# Tokens Used
label = Label(root, text="Used")
label.grid(row=5, column=main_cols)
entry_used = Entry(root, width=5)
entry_used.grid(row=6, column=main_cols)
entry_used.insert(END, "0")
# System Message
system_box = Text(root, width=30, height=main_height)
system_box.config(wrap=WORD)
system_box.grid(row=1, rowspan=main_height, column=0, columnspan=3, pady=5, padx=5)
# Chat Log
chat_box = Text(root, width=70, height=main_height)
chat_box.config(wrap=WORD)
chat_box.grid(row=1, rowspan=main_height, column=3, columnspan=4, pady=5, padx=5)
# chat_box['state'] = 'disabled'
# Chat Log
prompt_box = Text(root, width=100, height = 5)
prompt_box.grid(row=main_height+1, rowspan=1, column=0, columnspan=main_cols, pady=5, padx=5)

# Totals up the tokens
def count_tokens(text):
    tokens = tokenizer.encode(text)
    return len(tokens)

# Write text to the log file
def write(data):
    # open a file in write mode
    f = open("Log/" + date_time + ".html", "a", encoding="utf8")
    # write a string to the file
    f.write(str(data) + "\n")
    # close the file
    f.close()

# Writes the header of the HTML log file
def write_header():
    header = """<!DOCTYPE html>
    <html>
        <head>
            <style>
                div {
                    white-space: pre-wrap;
                    font-family: Lucida;
                    font-size: 24px;
                    text-align: justify;
                }
            </style>
        </head>
        <body>
    """
    write(header)

# Ends the HTML Log file (On Close)
def write_footer():
    write("</body>\n</html>")

# Adds a line of text to the log file
def write_line():
#    write("-"*60 + "\n")
    write("<hr>")

# Writes a paragraph to the log file
def write_block(text):
    write("<div>" + html.escape(text) + "</div>")
    write_line()

# Writes the session to the log file (at the beginning)
def write_session_hash():
    # Create and write a session hash
    write_block("Session: " + str(sha256.hexdigest()).upper())

# Writes the system text if it has changed
def maybe_write_system_text(system_text):
    global last_system_text
    if system_text != last_system_text:
        write_block("System: " + system_text)
        last_system_text = system_text

# Use the history to recreate the chat log
def rebuild_history():
    chat_box.delete("1.0", END)
    for item in history:
        chat_box.insert(END, item["role"].title() + ": " + item["content"] + "\n\n")
    chat_box.see(END)
    update_tokens_used()

# Count all the tokens in history and system
def update_tokens_used():
    token_count = count_tokens(system_box.get('1.0', END).strip())
    for h in history:
        token_count += count_tokens(h["content"])
    entry_used.delete(0, END)
    entry_used.insert(END, str(token_count))

# Count the tokens in a string
def prune_to(messages, max_size = 3072):
    token_count = count_tokens(messages[0]["content"])
    for m in range(len(messages[1:]),0,-1):
        token_count = token_count + count_tokens(messages[m]["content"])
        if token_count >= max_size:
            messages.pop(m)
    return messages

# Sends prompt to GPT
def send_prompt(prompt):
    global response
    # get system text
    system_text = system_box.get('1.0', END).strip()
    # log system text (if necessary)
    maybe_write_system_text(system_text)
    system_message_list = [{"role": "system", "content" : system_text}]
    # create new message or not
    if prompt:
        new_message = {"role": "user", "content": prompt}
        history.append(new_message)    
    if prompt.lower().startswith("can you"):
        # The assistant should assist
        new_message = {"role": "user", "content": "Of course I can. Would you like me to?"}
        history.append(new_message)
        rebuild_history()
    else:
        messages = system_message_list + history
        messages = prune_to(messages = messages)
        response = openai.ChatCompletion.create(
            model = box_models.get(),
            messages = messages,
            # max_tokens = int(text_tokens.get()),
            temperature = 1,
            stream = True,
            #banned words:     is         are       was         said
            logit_bias = {318: -100, 389: -100, 373: -100, 531: -100},
            user = str(sha256.hexdigest()).upper()
        )

# Clears out the text box and history
def reset():
    history.clear()
    rebuild_history()

def setButtonState(state):
    button_clear["state"] = state
    button_fix["state"] = state
    button_load["state"] = state
    button_refresh["state"] = state
    button_save["state"] = state
    button_submit["state"] = state
    button_undo["state"] = state


# Bundles above functions together
# And displays result
def submit(source=0):
    try:
        prompt = prompt_box.get('1.0', END).strip()
        # result = send_prompt(prompt)
        if prompt:
            chat_box.insert(END, "User: "  + prompt + "\n\n")
            write_block("User: " + prompt)
        chat_box.insert(END, "Assistant: ")
        send_prompt(prompt)
        setButtonState("disabled")
        prompt_box.delete("0.0", END)
    except openai.error.APIConnectionError as e:
        setButtonState("normal")
        showerror(title = "No API Connection", message = str(e))
    except openai.error.InvalidRequestError as e:
        setButtonState("normal")
        showerror(title = "Invalid Request", message = str(e))
    except openai.error.ServiceUnavailableError as e:
        setButtonState("normal")
        showerror(title = "Service Unavailable", message = str(e))
    except openai.OpenAIError as e:
        setButtonState("normal")
        showerror(title = type(e), message = str(e))

def undo():
    if len(history) == 0:
        return
    # remove last two items
    history.pop() # Assistant
    if not len(history):
        return
    role = history[-1]["role"]
    prompt_box.delete("1.0", END)
    if role == "user":
        prompt = history[-1]["content"]
        prompt_box.insert(END, prompt)
        history.pop() # User
    rebuild_history()


def fix_last_assistant():
    if len(history) == 0:
        return
    text_history = chat_box.get("1.0", END)
    search_string = "Assistant: "
    loc = text_history.rfind(search_string)
    if loc == -1:
        return
    loc += len(search_string)
    # remove last item
    history.pop() # Last assistant message
    history.append({"role": "assistant", "content": text_history[loc:].strip()})
    rebuild_history()

def save():
    filename = filedialog.asksaveasfilename(title="Save Chat File", initialdir = os.getcwd() + "\Chats", defaultextension = "json")
    if not filename:
        return
    f = open(filename, "w", encoding="utf8")
    savedata = []
    savedata.append({"role": "system", "content": system_box.get('1.0', END).strip()})
    savedata += history
    f.write(json.dumps(savedata))
    f.close()

def load():
    global history
    filename = filedialog.askopenfilename(title="Load Chat File", initialdir = os.getcwd() + "\Chats", filetypes = [("JSON Files", "*.json")])
    if not filename:
        return
    f = open(filename, "r", encoding="utf8")
    load_data = json.loads(f.read())
    f.close()
    system_data = load_data.pop(0)
    system_box.delete("1.0", END)
    system_box.insert(END, system_data["content"])
    history.clear()
    history += load_data
    rebuild_history()

# Do this every so often
def tick():
    global response
    global fulltext
    # Check to see if there is an active response
    if response:
        # If there is, get the next event
        event = next(response)
        # Check whether the event contains content or finishes the response
        event_text = event['choices'][0]['delta'].get('content')
        finish_reason = event['choices'][0].get('finish_reason')
        if event_text:
            # Add the new token to the full text
            fulltext += event_text
            # Write it in the chat box
            chat_box.insert(END, event_text)
            chat_box.see(END) 
        if finish_reason:
            history.append({"role": "assistant", "content": fulltext})
            write_block("Assistant: " + fulltext)
            rebuild_history()
            fulltext = ''
            response = None       
            setButtonState("normal")
    root.after(10, tick)

# Column of next button
colbutton = (i for i in range(13))
# Submit Button
button_submit = Button(root, text="Submit", command=submit)
button_submit.grid(row=main_height+2,column=next(colbutton),pady=5)
# Clear Button
button_clear = Button(root, text="Reset", command=reset)
button_clear.grid(row=main_height+2,column=next(colbutton))
# Refresh Button
button_refresh = Button(root, text="Refresh", command=rebuild_history)
button_refresh.grid(row=main_height+2,column=next(colbutton))
# Enter on Prompt
prompt_box.bind("<Control-Return>", submit)
'''
# TTS Button
button_tts = Button(root, text="Speak", command=speak)
button_tts.grid(row=31,column=5)
'''
# Undo Button
button_undo = Button(root, text="Undo", command=undo)
button_undo.grid(row=main_height+2,column=next(colbutton))
# Fix Button
button_fix = Button(root, text="Fix", command=fix_last_assistant)
button_fix.grid(row=main_height+2,column=next(colbutton))
# Save Button
button_save = Button(root, text="Save", command=save)
button_save.grid(row=main_height+2,column=next(colbutton))
# Load Button
button_load = Button(root, text="Load", command=load)
button_load.grid(row=main_height+2,column=next(colbutton))

# Main
write_header()
write_session_hash()
print("Main Loop")
root.after(100, tick)
root.mainloop()
write_footer()