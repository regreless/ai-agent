from pathlib import Path

builder_path = Path(r'C:\AIApp\ai-agent\resume-work\build_resume.py')
builder_text = builder_path.read_text(encoding='utf-8')
start_index = builder_text.index("doc.add_paragraph('核心技能'")
end_index = builder_text.index("doc.add_paragraph('工作经历'", start_index)
replacement_text = r"""source_doc = Document(r'C:\Users\Administrator\Desktop\刘谦-简历-精简版.docx')
doc.add_paragraph('专业技能', 'Heading 1')
for source_index in range(9, 30):
    source_text = source_doc.paragraphs[source_index].text.strip()
    if not source_text:
        continue
    if source_index == 19:
        doc.add_page_break()
        doc.add_paragraph('专业技能 续', 'Heading 1')
    if source_index in [9, 14, 19, 26]:
        doc.add_paragraph(source_text, 'Heading 2')
    else:
        add_text(source_text)

"""
builder_path.write_text(builder_text[:start_index] + replacement_text + builder_text[end_index:], encoding='utf-8')
