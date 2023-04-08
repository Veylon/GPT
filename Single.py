import openai
import requests
import json
import datetime
import hashlib
import html
from tkinter import *
from tkinter import ttk
from transformers import GPT2TokenizerFast
from gtts import gTTS
from playsound import playsound

# Load API Key
key_file = open("key.txt", "r")
openai.api_key = key_file.read()
key_file.close()

def models():
    data_dict = json.loads(str(openai.Model.list()))
    out = []
    for m in data_dict["data"]:
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
# Window Setup
root = Tk()
root.title("GPT 3.5 Interface: Session " + str(sha256.hexdigest()).upper())
root.option_add("*font", "lucida 16")
root.resizable(False,False)
# Models
label = Label(root, text="Model")
label.grid(row=1, column=7)
box_models = ttk.Combobox(root, width=15, state="readonly", values=models())
# box_models = ttk.Combobox(root, width=15, state="readonly", values=["text-davinci-003", "text-chat-davinci-002-20221122", "text-curie-001", "code-cushman-001"])
box_models.set("text-davinci-003")
box_models.grid(row=2, column=7, padx=5, pady=1)
# Tokens
label = Label(root, text="Tokens")
label.grid(row=3, column=7)
text_tokens = Entry(root, width=5)
text_tokens.grid(row=4, column=7)
text_tokens.insert(END, "1024")
# Tokens Used
label = Label(root, text="Used")
label.grid(row=5, column=7)
entry_used = Entry(root, width=5)
entry_used.grid(row=6, column=7)
entry_used.insert(END, "0")
# Moderation
text_mods = [Entry(root, width=5), Entry(root, width=5), Entry(root, width=5), Entry(root, width=5), Entry(root, width=5), Entry(root, width=5), Entry(root, width=5)]
label_mods = [Label(root, text=categories[0]), Label(root, text=categories[1]), Label(root, text=categories[2]), Label(root, text=categories[3]), Label(root, text=categories[4]), Label(root, text=categories[5]), Label(root, text=categories[6])]
for i in range(7):
    label_mods[i].grid(row=i*2 + 1, column=8, padx=5, pady=1)
    text_mods[i].grid( row=i*2 + 2, column=8, padx=5, pady=1)
# Input/Output
text_box = Text(root, width=100, height=40)
text_box.config(wrap=WORD)
text_box.grid(row=1, rowspan=30, column=1, columnspan=5, pady=5, padx=5)

# Totals up the tokens
def count_tokens(text):
    tokens = tokenizer.encode(text)
    return len(tokens)

# Displays the number of tokens
def show_token_count():
    count = count_tokens(text_box.get('1.0', END))
    entry_used.delete(0, END)
    entry_used.insert(END, count)

# Plans to show token count later
def make_token_update(self):
    if (token_count_job):
        root.after_cancel(token_count_job)
    root.after(1000, show_token_count)

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

def get(url):
    headers = {
        'Authorization': 'Bearer ' + openai.api_key
    }
    r = requests.get(url)
    r.raise_for_status()
    return r
    

# Sends prompt to GPT
def send_prompt(prompt):
    response = openai.Completion.create(
        model = box_models.get(),
        prompt = prompt,
        max_tokens = int(text_tokens.get()),
        temperature = 1,
        top_p = 1,
        n = 1,
        logit_bias = {318: -100, 389: -100, 373: -100, 531: -100},
        echo = True,
        user = "Session " + str(sha256.hexdigest()).upper()
    )
    return response['choices'][0]['text'].lstrip().rstrip()

# Displays information related to moderation from GPT
def describe_moderation(moderation, show = False):
    scores = moderation["results"][0]["category_scores"]
    # print(scores)
    #print any spicy categories
    used = False
    i = 0
    mod_block = ""
    for category, score in scores.items():
        text_mods[i].delete(0,END)
        int_score = int(round(score,2)*100)
        text_mods[i].insert(END, int_score)
        label_mods[i].config(text=category.capitalize())
        if int_score > 0 or show:
            used = True
            mod_block += category.capitalize() + ": " + str(round(score*100,2)) + " "
        i += 1
    if used:
        mod_block += "\n"
    #note if they are also flagged
    i=0
    for result in moderation['results']:
        for category, flag in result['categories'].items():
            if flag:
                # Mark the appropriate entries
                text_mods[i].insert(END,"!!")
                mod_block += category.capitalize() + ": Flagged\n"
            elif show:
                text_mods[i].insert(END,"!!")
                mod_block += category.capitalize() + ": NOT Flagged\n"
            i += 1
    if(used):
        write_block(mod_block)
    return

# Clears out the text box
def clear():
    text_box.delete('1.0', END)

# Send current text to moderation
def moderate():
    try:
        text = text_box.get('1.0', END)
        write_block(text)
        describe_moderation(openai.Moderation.create(input = text))
    except requests.HTTPError as e:
        text_box.insert(END, "HTTP Error Occurred:\n" + str(e))

# Bundles above functions together
# And displays result
def submit(source=0):
    try:
        prompt = text_box.get('1.0', END)
        result = send_prompt(prompt)
        clear()
        text_box.insert(END, result)
        moderate()
#        write_block(result)
#        describe_moderation(openai.Moderation.create(input = result))
    except requests.HTTPError as e:
        text_box.insert(END, "\n\nHTTP Error Occurred:\n" + str(e))
    
def speak():
    text = ""
    if text_box.tag_ranges(SEL):
        text = text_box.get(SEL_FIRST, SEL_LAST)
    else:
        text = text_box.get('1.0', END)
    tts = gTTS(text=text, lang='en', tld='co.za',slow=False)
    filename ='speech.mp3'
    tts.save(filename)
    playsound(filename, block=False)

# Ctrl-Return to submit as well
text_box.bind('<Control-Return>', submit)
# Any key to update tokens
text_box.bind('<KeyPress>', make_token_update)
# Submit Button
button_submit = Button(root, text="Submit", command=submit)
button_submit.grid(row=31,column=1,pady=5)
# Moderate Button
button_moderate = Button(root, text="Moderate", command=moderate)
button_moderate.grid(row=31,column=2)
# Clear Button
button_clear = Button(root, text="Clear", command=clear)
button_clear.grid(row=31,column=3)
# TTS Button
# button_tts = Button(root, text="Speak", command=speak)
# button_tts.grid(row=31,column=5)

# Main
write_header()
write_session_hash()
root.mainloop()
write_footer()