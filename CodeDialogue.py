import openai
from transformers import GPT2TokenizerFast


# Load API Key
print("Loading API Key")
with open("key.txt", "r") as keyfile:
    openai.api_key = keyfile.read()

# Define the topic variable
topic = """a boy's love for his mother"""

# Define the actors
actors = [
    "Sigmund Freud",
    "Carl Jung"
]
# Potentially have different preprompts for each of the actors
preprompts = [
    "Your purpose is to roleplay {0} arguing with {1} about {2}. You frequently use German words instead of English.",
    "Your purpose is to roleplay {0} arguing with {1} about {2}."
]

# Remove quotes if the whole thing is a quote
def strip_quotes(text):
    if text[0] == '\"' and text[-1] == '\"' and text.count('\"') == 2:
        return text[1:-2]
    return text

# Make it so that OpenAI sees the current actor as the assistant and the other one as the user
def format_history(my_name, history):
    formatted_history = []
    for entry in history:
        role = "user"
        if entry["role"] == my_name:
            role = "assistant"
        formatted_history.append({"role": role, "content": entry["content"]})
    return formatted_history

# Generate the next line of dialogue
def next_line(my_name, other_name, topic, preprompt, history):
    # Format the history in OpenAI's style
    my_history = format_history(my_name, history)
    # Format the preprompt
    preprompt = [{"role": "system", "content": preprompt.format(my_name, other_name, topic)}]
    my_history = preprompt + my_history
    completions = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        stop="\n", # Keeps actors from writing each other's lines
        timeout=30,
        temperature=0.9,
        messages=my_history
    )
    content = completions["choices"][0]["message"]["content"].strip().replace("\n", "")
    content = strip_quotes(content)
    return content

# Because sometimes the responses include the actor's name and sometimes they don't.
def print_using_colon(entry):
    index = entry["content"].find(":")
    if index >= 0 and index < len(entry["role"]) + 1:
        print(entry["content"])
    else:
        print(entry["role"] + ": " + entry["content"])

# Sometimes the conversation ends early
def is_goodbye(history):
    if len(history) < 10: return False
    goodbye_count = 0
    # Check the last couple entries for "goodbye" language
    for entry in range(-1,-3,-1):
        for text in ["goodbye", "goodnight", "farewell", "the end", "thank you"]:
            if text in history[entry]["content"].lower():
                goodbye_count += 1 
    # If they're both saying it, then it really is goodbye
    return goodbye_count == 2

# Prune History (Too many tokens)
tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
def prune_history(history, max_size = 3072):
    token_count = 0
    # Count backwards so we prune the earliest entries
    for entry in range(len(history[1:]),0,-1):
        token_count += len(tokenizer.encode(history[entry]["content"]))
        if token_count >= max_size:
            history.pop(entry)
    return history

# The main loop
def talk_to_self(topic):
    # history of conversation
    history = []
    print(f"Roleplaying {actors[0]} and {actors[1]} discussing {topic}.")
    # Loop many times
    for i in range(20):
        # Get first actor's statement
        history.append({"role": actors[0], "content": next_line(actors[0], actors[1], topic, preprompts[0], history)})
        print("\t" + history[-1]["content"])
        if is_goodbye(history): break
        # Get second actor's statement
        history.append({"role": actors[1], "content": next_line(actors[1], actors[0], topic, preprompts[1], history)})
        print("\t" + history[-1]["content"])
        # Prune history to avoid too many tokens
        prune_history(history, 1024)
        if is_goodbye(history): break


if __name__ == '__main__':
    talk_to_self(topic)