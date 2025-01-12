class SimpleProp:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def __eq__(self, other):
        return self.name == other.name

    def __str__(self):
        return self.name + ' ' + str(self.age)



def try_hints(x: int):
    print('everything is ok')
    print(x)


def get_sum_of_dict():
    dict_ = {
        'a': 10.2,
        'b': 15.33,
        'c': 122.32
    }
    print(sum(dict_.values()))

def dict_comprehension():
    arr_ = [
            {
              "ownershipType": "Спільна власність",
              "percent-ownership": "34",
              "rightBelongs": "1"
            },
            {
              "ownershipType": "Спільна власність",
              "rights_id": "1536056884190",
              "percent-ownership": "33",
              "rightBelongs": "1536056884190"
            },
            {
              "ownershipType": "Спільна власність",
              "rights_id": "1",
              "percent-ownership": "33",
              "rightBelongs": "1536057453629"
            }
          ]
    dict_ = {item['rightBelongs']:item['percent-ownership'] for item in arr_}
    print(dict_)

def dict_intersection():
    dict_ = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6}
    dict2_ = {'c': 3, 'f': 7, 'v': 34}
    dict3_ : dict[str : int] = {}
    print(bool(dict_) and bool(dict2_) and bool(dict3_))
    print(dict3_)
    print(dict_.keys() & dict2_.keys())


if __name__ == '__main__':
    # dict_comprehension()
    # x_ = {'a': 1, 'b': 2, 'c': []}
    # print bool(x_['c'])
    # dict_intersection()
    # for xo, val in {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6}.items():
    #     print(val)
    x = ('2022', '2024')
    for i in range(int(x[0]), int(x[1])+1):
        print(i)