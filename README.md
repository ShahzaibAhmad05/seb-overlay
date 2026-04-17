## Safe Exam Browser Overlay

> [!IMPORTANT]
> This repository is only meant to **expose the unsafe side** of safe exam browser and indirectly give the original developers ideas to make it safer.
>
> I am NOT responsible for anyone using this overlay project in any way as it is not open-source. Further details are explicitly stated in the [LICENSE]().


This documentation bellow is fully typed by me. I appreciate anyone reading. One thing to note is that in some places I have used the acronym SEB which essentially just means **Safe Exam Browser**.

And for the sake of simplicity, I have not considered MacOS users for this project since neither do I nor any of my friends have a Mac.


### If you are here to just patch SEB and cheat in Exams

This is not the project you are looking for. But you might find it [here]().


## What did I do

I am using an existing patch for SEB which can be setup using the instructions in [the section bellow]. After applying this patch safe browser is modified. Now it will not stop the user from opening an instance of an LLM in another desktop view.

However, as you may observe bellow, this patched version of safe browser looks quite different from the original one. The windows taskbar is now visible and some buttons have changed their styling. The changes are quite noticable actually.

[IMAGES]


## What I tried (and absolutely did not work)

- You might be thinking of resolving the taskbar issue by making it auto-hide (which is available in windows settings) as in:

[IMAGE]

but this still looks different because SEB has it's own custom taskbar which is not visible in the patch. Another issue with this solution is that the instructor could potentially see you accidently moving your mouse to the bottom of the screen and the windows taskbar coming up (which is obviously going to be a problem).

- I had one of my friends run SEB in a virtual machine to overcome it's restrictions but this trick straight up failed (nicely played by the developers). 

- Another solution would be to disable the taskbar and the shortcut keys on windows completely but again, SEB has it's own custom taskbar which we cannot get without an overlay on the screen, and just to be realistic here, why bother disabling half of your convenience just for a simple exam? There is a nice solution to all of this, exactly **what I came up with**.


## What I came up with

These imperfections in the patch are where this repository comes in. It basically has two modules:

- An Overlay (the important one)

This is exactly what it sounds like. An overlay, a few elements on top of your windows screen using `.png` images. These cover for the visible windows taskbar and the modified buttons on the patch.

As for the shortcut keys, they are temporarily disabled when the script is run. Details for which keys are disabled are [here]().

- MCQ solver using OCR

Since our shortcut keys are disabled, now we have to figure out some way to actually solve an exam without the instructor noticing us pressing a lot of buttons on our keyboards. AND for the sake of an example lets assume our exam to be Multiple Choice Questions (MCQ-based).

A nice way around it would be to use [tesseract OCR]() in a python script to read the question on the screen and use some LLM-based api to solve it. Assuming we all want this to be free I have considered using [Gemini](https://gemini.com) for this task. 

And, for the sake of avoiding pressing/holding a lot I have considered using only two keys of the user's choice (configurable in `config.json`). One takes the OCR of the screen to capture a question, and the other displays the answer to the captured question on the screen.


## Setup (this is very complex, trust)

MAKE SURE YOU ARE ON WINDOWS or MacOS and you have python installed!!

> SEB does not run on linux

1) Go to your projects folder, clone this repository and enter it:

```bash
git clone https://github.com/ShahzaibAhmad05/seb-overlay
cd seb-overlay
```

2) Activate a virtual environment and activate it **(optional, skip if you are unfamiliar)**:

```bash
# it will work with older/newer versions as well
# but I have used this one
py -3.13 -m venv .venv
```

3) Install the requirements:

```bash
pip install -r requirements.txt
```

3) Install Safe Exam Browser [VERSION] (the original one) from [here]().

4) Close everything on your desktop and run capture module. This will snip and save images into `/assets`

```bash
python -m capture
```

5) Now it's time to patch SEB. Download the patch [VERSION] from [here](), and run it.

6) Open SEB on your desktop to make sure it is patched. It should look like this:

[IMAGE]

7) Open the `seb-overlay` project again. Run the overlay:

```bash
python -m overlay
```

8) An overlay will popup on the screen. It will stay on the top of the screen by default. There is a key `TOGGLE_OVERLAY` in `config.json`. By default it is set to *Ctrl+Alt+T* which is the safest I could figure out. `Win` key is disabled automatically by this script.

9) Make sure to turn off these shortcuts from windows settings "in the name of safety": 

```txt
Ctrl+Win+ArrowKey -> Changes the desktop view
Three/Four finger swipe -> Opens Task View
```

I prefer not to write an extra 50-line documentation on how to turn these off, so figure it out on runtime. Rest of the steps on the setup are completely optional. 

I would want you to find your own way to solve your exam from here since you have the overlay module running.

10) Now SEB should look real. But since we turned off our VERY useful shortcut keys, we have to use the `mcq` module to be able to solve the exam. First create the `.env` file using the command bellow and put in your Gemini api keys, which you can get from [here]().

```bash
cp .env.example .env
```

11) Now run the `mcq` module:

```bash
python -m mcq
```

12) The default keys for using this script would be `M` for the OCR, and `L` for displaying the answer. You may also need to put your gemini api keys in `.env` 

13) Now when you press `M`, an OCR is taken, and after a time interval of a few seconds, the answer is fetched and saved. When you press `L`, the answer will display at the corner of your screen.

> [!NOTE]
> I hope at this point it is clear how this works. If you have any confusions setting this up, feel free to open an issue here. I would reply.

