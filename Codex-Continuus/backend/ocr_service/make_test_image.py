from PIL import Image, ImageDraw, ImageFont
img = Image.new("RGB", (1200, 200), "white")
draw = ImageDraw.Draw(img)
draw.text((20, 80), "Gallia est omnis divisa in partes tres.", fill="black", font=ImageFont.load_default())
img.save("latin_test.png")
print("Wrote latin_test.png")