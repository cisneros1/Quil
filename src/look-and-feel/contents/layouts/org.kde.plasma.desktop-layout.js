// {{full_name}} desktop layout.
// Runs only when the theme is applied with "Desktop and window layout" checked
// (or `plasma-apply-lookandfeel --resetLayout`). For now this is Plasma's default
// bottom panel; customize it here once we design Quil's panel.

loadTemplate("org.kde.plasma.desktop.defaultPanel")

var desktopsArray = desktopsForActivity(currentActivity());
for (var j = 0; j < desktopsArray.length; j++) {
    desktopsArray[j].wallpaperPlugin = 'org.kde.image';
}
