from PIL import Image, ImageDraw
import datetime

# 生成一个简单的图片
width, height = 400, 200
image = Image.new('RGB', (width, height), (255, 255, 255))
draw = ImageDraw.Draw(image)

# 添加当前时间文本
text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
draw.text((50, 80), text, fill=(0, 0, 0))

# 保存图片
image.save("generated_image.png")

print("Image generated successfully!")
