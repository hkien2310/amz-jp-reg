import asyncio
import random
import math

async def human_mouse_move(page, end_x, end_y, steps=15):
    """Mô phỏng đường cong chuột giống người với Jitter (độ rung)"""
    if not hasattr(page, 'last_mouse_pos'):
        page.last_mouse_pos = (random.randint(100, 800), random.randint(100, 600))
    start_x, start_y = page.last_mouse_pos
    
    # Random số bước để không cố định
    actual_steps = random.randint(12, 25)
    
    # Điểm control point bị lệch hẳn ra ngoài để tạo đường vòng
    control_x = (start_x + end_x) / 2 + random.randint(-150, 150)
    control_y = (start_y + end_y) / 2 + random.randint(-150, 150)

    for i in range(actual_steps + 1):
        t = i / actual_steps
        # Bezier curve
        x = (1 - t)**2 * start_x + 2 * (1 - t) * t * control_x + t**2 * end_x
        y = (1 - t)**2 * start_y + 2 * (1 - t) * t * control_y + t**2 * end_y
        
        # Thêm Jitter (độ rung lắc ngẫu nhiên ở mỗi pixel)
        jitter_x = random.uniform(-3, 3)
        jitter_y = random.uniform(-3, 3)
        
        # Càng về đích độ rung càng giảm để click chính xác
        if t > 0.8:
            jitter_x /= 2
            jitter_y /= 2
            
        await page.mouse.move(x + jitter_x, y + jitter_y)
        # Delay ngẫu nhiên không đồng đều giữa các bước
        await asyncio.sleep(random.uniform(0.005, 0.025))
    
    # Di chuyển bước cuối vào chính xác target
    await page.mouse.move(end_x, end_y)
    page.last_mouse_pos = (end_x, end_y)

async def click_element(page, selector):
    """Hover tự nhiên và click"""
    element = await page.query_selector(selector)
    if not element:
        return False
        
    box = await element.bounding_box()
    if not box:
        return False
        
    # Điểm đích ngẫu nhiên trong phần tử
    target_x = box['x'] + random.uniform(box['width'] * 0.2, box['width'] * 0.8)
    target_y = box['y'] + random.uniform(box['height'] * 0.2, box['height'] * 0.8)
    
    await human_mouse_move(page, target_x, target_y)
    await page.mouse.down()
    await asyncio.sleep(random.uniform(0.05, 0.15)) # Giữ chuột một chút
    await page.mouse.up()
    return True

async def human_type(page, selector, text):
    """Gõ phím từng chữ với tốc độ ngẫu nhiên, mô phỏng lỗi vặt"""
    element = await page.query_selector(selector)
    if not element:
        return False
        
    await click_element(page, selector)
    for char in text:
        # 2% tỉ lệ gõ sai xong xoá
        if random.random() < 0.02 and char.isalpha():
            wrong_char = chr(ord(char) + random.randint(1, 3))
            if wrong_char.isalpha():
                await element.type(wrong_char, delay=random.randint(40, 100))
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
        # Gõ chữ thật
        await element.type(char, delay=random.randint(30, 150))
        
        # Thỉnh thoảng ngập ngừng
        if random.random() < 0.05:
            await asyncio.sleep(random.uniform(0.2, 0.6))
        else:
            await asyncio.sleep(random.uniform(0.01, 0.08))
    return True
