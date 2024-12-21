import re
def text2int(textnum, numwords={}):
    if not numwords:
      units = [
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen",
      ]

      tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

      scales = ["hundred", "thousand", "million", "billion", "trillion"]

      numwords["and"] = (1, 0)
      for idx, word in enumerate(units):    numwords[word] = (1, idx)
      for idx, word in enumerate(tens):     numwords[word] = (1, idx * 10)
      for idx, word in enumerate(scales):   numwords[word] = (10 ** (idx * 3 or 2), 0)

    current = result = 0
    for word in textnum.split():
        if word not in numwords:
          raise Exception("Illegal word: " + word)

        scale, increment = numwords[word]
        current = current * scale + increment
        if scale > 100:
            result += current
            current = 0

    return result + current

def convert_command(command):
    number_word_pattern = re.compile(r'\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|'
                                     r'thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|'
                                     r'twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|'
                                     r'hundred|thousand|million|billion|trillion|and)+\b', re.IGNORECASE)

    matches = number_word_pattern.findall(command)

    for match in matches:
        try:
            number_value = text2int(match.lower())  
            command = command.replace(match, str(number_value), 1)
        except Exception as e:
            print(f"Error converting '{match}': {e}")

    return command