from docxtpl import DocxTemplate
import os

template_path = os.path.join('templates', 'report_template.docx')
output_path = os.path.join('output', 'report_filled_test.docx')

# Тестовые данные для заполнения
context = {
    'executor': 'Иванов И.И.',
    'date': '27.05.2025',
    'signer': 'Петров П.П.',
    'approver': 'Сидоров С.С.'
}

def fill_report_template(template_path, context, output_path):
    """
    Заполняет шаблон докладной записки тестовыми данными.
    """
    doc = DocxTemplate(template_path)
    doc.render(context)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    print(f'Документ успешно создан: {output_path}')

if __name__ == '__main__':
    fill_report_template(template_path, context, output_path) 