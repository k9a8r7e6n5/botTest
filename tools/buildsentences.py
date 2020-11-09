import xlwings as xw
import re
import random

wb = xw.Book('D:/Hibay/产品相关/酒店/iHotel/botService/doc/RequirementDoc/SentencePatten.xlsx')
sht = wb.sheets[0]
#component中的所有列
colum = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z',
         'aa','ab','ac','ad','ae','af','ag','ah','ai','aj','ak','al','am','an','ao','ap','aq','ar','as','at','au','av','aw','ax','ay','az',
         'ba','bb','bc','bd']
#colum = ['a','b','c']

#定义数组，slotname存储第一行的所有slot 名字
# slot存储每一列的slot value
slotname = []
i=0
slot = [i for i in range(len(colum))]
#定义词典，存储slot k:v
slot_dict = {}
#对component进行解析，存入数组
i = 0
for col in colum:
    #第一行
    rng = sht.range(col+str(1)).expand('table')
    nrows = rng.rows.count
    slot[i] = sht.range(f'%s:%s{nrows}' % (col+str(1),col)).value
    slotname.append(slot[i][0])
    del slot[i][0] #去掉表头
    #存入词典k:v
    slot_dict[slotname[i]] = slot[i]
    i = i + 1

#print(slotname)
#for k in slot:
#    print(k)
#print(slot_dict)
####################################################################

def generateSentences(sheet, filepath):

    print("#################sheet is %s" % sheet)
    #output
    output_text = 'D:/Hibay/产品相关/酒店/iHotel/botService/tools/' + filepath
    output_excel = 'D:/Hibay/产品相关/酒店/iHotel/botService/tools/senteces.xlsx'
    output_wb = xw.Book(output_excel)
    sht = output_wb.sheets(filepath)
    sht.range('a1:b500').clear()

    ##############
    #定义sentence数组，存储一个sheet中的所有句子
    sentences = []
    rng = sheet.range('b1').expand('table')
    nrows = rng.rows.count
    sentences = sheet.range(f'b1:b{nrows}').value
    del sentences[0] #去掉表头

    #定义句子中的slot数组
    i=0
    sentence_slot = [i for i in range(len(sentences))]

    #处理每一个句式，由slot取随机值，生成n个随机句子，写入文本文件
    with open(output_text,'w+') as file:
        j = 0
        k = 1
        for s in sentences:
            #print(s)
            #正则获取{}之间的所有slot字符串
            print(s)
            sht.range('a' + str(k)).value = s
            k = k+1
            file.writelines(s.replace('\u200b', '') + '\n')
            sentence_slot[j] = re.findall(r'[{](.*?)[}]', s)
            #print(sentence_slot[j])
            # 每个句式，随机生成n个句子
            n = 3
            for num in range(0, n):
                sentence = s
                for ss in sentence_slot[j]:
                    rand = random.randint(0,len(slot_dict[ss])-1)
                    bb = slot_dict[ss][rand]
                    sentence = sentence.replace('{'+ss+'}', bb)

                print(sentence)
                sht.range('b'+str(k)).value = sentence
                k = k+1
                file.writelines(sentence.replace('\u200b','') + '\n')

            j=j+1

    output_wb.save()
    output_wb.close()

#处理sentence sheet
f1 = 'requestItems'
f2 = 'repairItems'
f3 = 'requestInformation'
f4 = 'requestMessage'
f5 = 'requestCallBack'

sht_1 = wb.sheets[1]
sht_2 = wb.sheets[2]
sht_3 = wb.sheets[3]
sht_4 = wb.sheets[4]
sht_5 = wb.sheets[5]

generateSentences(sht_1, f1)
generateSentences(sht_2, f2)
generateSentences(sht_3, f3)
generateSentences(sht_4, f4)
generateSentences(sht_5, f5)