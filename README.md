# Noteab's Biome Macro notice.
## I. Introduction
1) New developer??!?
- Hi everyone. I will be replacing Noteab as the main developer/maintainer for Noteab's Biome Macro. I am Vapure, aka "criticize." or "C". If you have any enquires, feel free to contact me on discord `criticize.` or by email `work.vapure@gmail.com`.
- I am the current manager/director for Scope Team, you might have seen me somewhere inside other Sol's RNG related servers.
2) The project.
- This project is a fork of the original [Noteab's Biome Macro](https://github.com/noteab/Noteab-Macro/).
- Abides by the [Apache 2.0 license](https://github.com/noteab/Noteab-Macro/blob/main/LICENSE).
  - Even if [Noteab's notice](https://github.com/noteab/Noteab-Macro/blob/main/NOTICE.txt) states that "Users must request explicit permission from Noteab and get accepted before using core macro functions and any related asset in the macro.", however Noteab's macro abides by the [Apache 2.0 license](https://github.com/noteab/Noteab-Macro/blob/main/LICENSE), he is not legally allowed to stop anyone from redistributing the code, his statement strongly contradicts with the type of license he's using.
## II. About Noteab's Biome Macro.
1) What does Noteab Biome Macro offer?
- Merchant detections using two methods, OCR detection and logs reading detection.
  - Auto purchase from merchants.
- Biome detections, 99.99% accurate most of the time using logs reading method.
- Aura detections, again, 99.99% accurate most of the time using logs reading method.
- Webhooks for notification to your Discord server!!
- Auto popping potions inside of "Glitched biome".
- Allowing for mouse clicks to prevent disconnection from the game. Very suitable for afk sessions packed with features.
- Multi webhook support.
- Macro session time report.
2) The future route of Noteab's Macro.
- I will be maintaining biome detections in the future, as well as adding other auras to the game.
- I will attempt to enhance the UX (user experience) for Noteab's Biome Macro, allowing more customizations.
- A lot of new features are being planned to add currently.
## III. Ending statement
- Noteab have permanently stepped down from the position of the owner and developer for Noteab's macro, that is a really sudden and unfortunate news for not only me but I believe for a lot of people. Since this is one of the biggest Sol's macro, it would be unsuitable if no one continues to maintain it. If you are looking for other alternatives for Noteab's Biome Macro, I suggest checking out [Scope Team](https://discord.gg/vuHAR97FWZ). But for now, I will be trying my absolute best as the lead developer for Noteab's Biome Macro, and I look forward to work with everyone.
## IV. FAQs and common fixes
Q: Macro has virus?<br>
A: No, it is Window's false positives. You can check out the source code or reverse engineer if you wish. Or put the file into a virtual machine/Virus Total.<br>
Q: Some detection features doesn't work?<br>
A: Apply these FFlags. [How to apply FFlags](https://www.youtube.com/watch?v=4ryeAMV3fLM).<br>
```
{
  "DFFlagDebugPerfMode": "True",
  "FFlagHandleAltEnterFullscreenManually": "False",
  "FStringDebugLuaLogPattern": "ExpChat/mountClientApp",
  "FStringDebugLuaLogLevel": "trace"
}
```
<br>
Q: I got this bug "Exception: Unsupported locale setting":<br>
A: https://i.postimg.cc/ZqBXBFfG/image.png<br>
Q: How to calibrate merchants?<br>
A: https://i.postimg.cc/3NdGYNrF/image.png & https://i.postimg.cc/15VFd8j9/image.png<br>
Q: Where is Eden detection?<br>
A: It is on by default and you cannot turn it off.<br>
Q: What is the first item slot?<br>
A: https://i.postimg.cc/9X6tt3Wg/image.png<br>
Q: Why doesn't merchant detection work? I tried calibrating but nothing works.<br>
A: Install Tesseract OCR: https://github.com/tesseract-ocr/tesseract/releases/tag/5.5.1<br>
