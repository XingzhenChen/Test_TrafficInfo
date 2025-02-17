from PIL import Image, ImageDraw
import datetime

# 生成一个简单的图片
width, height = 400, 200
image = Image.new('RGB', (width, height), (255, 255, 255))
draw = ImageDraw.Draw(image)

# 获取当前时间
current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# 在图片上写入时间
draw.text((50, 80), current_time, fill=(0, 0, 0))

# 保存图片，文件名包含时间戳
image_filename = f"generated_image_{timestamp}.png"
image.save(image_filename)

print(f"Image generated and saved as {image_filename}")
